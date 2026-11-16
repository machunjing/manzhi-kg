# -*- coding: utf-8 -*-
"""
把 6 份中文指南 PDF 解析成文本、按 300 字/50 重叠切块，灌进 manzhi_real

为什么单独一个脚本：
  pubmed_records.json 里的 5,026 篇文献全是英文，中文语料只在指南 PDF 里。
  中文问答要能检索到中文证据，就必须先把指南切块入库。

用法：py -3.8-64 db/import_guides.py
可重复执行（先删 DG 开头的旧数据）
"""
import io
import os

def _pw():
    """数据库口令：环境变量优先，其次同目录 .env（.env 不进版本库）"""
    v = os.environ.get("MYSQL_PASSWORD")
    if v:
        return v
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            for ln in f:
                if ln.strip().startswith("MYSQL_PASSWORD="):
                    return ln.split("=", 1)[1].strip()
    return ""

import re
import sys
import time

import fitz  # PyMuPDF
import pymysql

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), "数据包")
DB = "manzhi_real"

CHUNK_SIZE = 300
OVERLAP = 50

# 文件名 -> (文献ID, 疾病维度, 发布机构, 年份)
GUIDES = [
    ("中国血脂管理指南2023年.pdf", "DG001", "血脂异常", "中国血脂管理指南修订联合专家委员会", 2023),
    ("中国血脂管理指南_基层版2024年_.pdf", "DG002", "血脂异常", "中国血脂管理指南修订联合专家委员会", 2024),
    ("中国高血压防治指南2024修订版.pdf", "DG003", "高血压", "中国高血压防治指南修订委员会", 2024),
    ("国家基层高血压防治管理指南2025版.pdf", "DG004", "高血压", "国家心血管病中心", 2025),
    ("全面管理血脂相关心血管风险专家共识（2025）.pdf", "DG005", "血脂异常", "中国血脂管理专家组", 2025),
    ("成人高脂血症食养指南2023年版.pdf", "DG006", "血脂异常", "国家卫生健康委员会", 2023),
]


def clean(text):
    """去页眉页脚残留、合并断行、压缩空白"""
    text = text.replace("\u3000", " ")
    text = re.sub(r"[\u200b\ufeff]", "", text)
    # 中文之间的换行直接删掉（PDF 硬折行），英文单词间保留空格
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*\n\s*(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    # 去掉纯页码行
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln and not re.fullmatch(r"[-—\s]*\d{1,4}[-—\s]*", ln)]
    return "\n".join(lines)


def chunk(text):
    out, i = [], 0
    while i < len(text):
        piece = text[i:i + CHUNK_SIZE].strip()
        if len(piece) >= 60:            # 太碎的块没有检索价值
            out.append(piece)
        if i + CHUNK_SIZE >= len(text):
            break
        i += CHUNK_SIZE - OVERLAP
    return out


def main():
    t0 = time.time()
    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root", password=_pw(),
                           database=DB, charset="utf8mb4", autocommit=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM documents WHERE id LIKE 'DG%%'")   # 切块随外键级联删除
    conn.commit()

    total_doc = total_chunk = 0
    for fname, did, disease, org, year in GUIDES:
        path = os.path.join(PKG, fname)
        if not os.path.exists(path):
            print("  [跳过] 找不到 %s" % fname)
            continue
        doc = fitz.open(path)
        raw = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        text = clean(raw)
        pieces = chunk(text)

        cur.execute(
            "INSERT INTO documents (id,pmid,title,title_en,authors,journal,doc_type,disease,"
            "source,publish_date,chunk_count,status,doi,url,abstract,mesh) "
            "VALUES (%s,NULL,%s,NULL,NULL,%s,'临床指南',%s,'本地指南文件',%s,%s,'已入库',"
            "NULL,NULL,%s,NULL)",
            (did, fname.replace(".pdf", ""), org, disease,
             "%d-01-01" % year, len(pieces), text[:2000]))
        rows = [("CG%s%04d" % (did[2:], i), did, i, disease, len(p), p)
                for i, p in enumerate(pieces)]
        cur.executemany(
            "INSERT INTO chunks (id,doc_id,chunk_idx,disease,text_len,text) "
            "VALUES (%s,%s,%s,%s,%s,%s)", rows)
        conn.commit()
        total_doc += 1
        total_chunk += len(pieces)
        print("  %-8s %-46s %6d 字 -> %3d 块" % (did, fname[:44], len(text), len(pieces)))

    print("-" * 70)
    cur.execute("SELECT COUNT(*) FROM documents WHERE source='本地指南文件'")
    print("  指南文献 %d 篇" % cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM chunks WHERE doc_id LIKE 'DG%%'")
    print("  指南切块 %d 条" % cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM documents")
    print("  documents 合计 %d 篇" % cur.fetchone()[0])
    cur.execute("SELECT COUNT(*) FROM chunks")
    print("  chunks 合计 %d 条" % cur.fetchone()[0])

    # 中文全文检索验证
    for w in ["血脂", "糖尿病", "高血压", "他汀", "低密度脂蛋白"]:
        cur.execute("SELECT COUNT(*) FROM documents WHERE MATCH(title,abstract) AGAINST(%s IN BOOLEAN MODE)", (w,))
        print("  全文命中 %-8s %d 篇" % (w, cur.fetchone()[0]))
    for w in ["他汀", "血压测量"]:
        cur.execute("SELECT COUNT(*) FROM chunks WHERE MATCH(text) AGAINST(%s IN BOOLEAN MODE)", (w,))
        print("  切块命中 %-8s %d 条" % (w, cur.fetchone()[0]))

    cur.close()
    conn.close()
    print("-" * 70)
    print("完成，用时 %.1f 秒" % (time.time() - t0))


if __name__ == "__main__":
    sys.exit(main())
