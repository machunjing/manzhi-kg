# -*- coding: utf-8 -*-
"""全局配置"""
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

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

# ---- MySQL ----
MYSQL = dict(host="127.0.0.1", port=3306, user="root", password=_pw(), charset="utf8mb4")

DB_DEMO = "manzhi"        # 演示库：数字与前端页面一致
DB_REAL = "manzhi_real"   # 真实库：检索与问答

# ---- 服务 ----
HOST = "0.0.0.0"
PORT = 5001
DEBUG = False

# ---- 检索参数 ----
BM25_TOPK = 30            # 关键词路召回数
VEC_TOPK = 30             # 向量路召回数
GRAPH_TOPK = 20           # 图谱路召回数
RRF_K = 60                # RRF 平滑常数
FINAL_TOPK = 8            # 最终送进答案的条数
MIN_SCORE = 0.0

# TF-IDF 字符 n-gram（中文不依赖分词，英文靠 3-gram 也能召回）
TFIDF_ANALYZER = "char_wb"
TFIDF_NGRAM = (2, 3)
TFIDF_MAX_FEATURES = 300000
