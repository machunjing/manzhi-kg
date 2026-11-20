# -*- coding: utf-8 -*-
"""MySQL 连接与查询 helper

Flask 用 threaded=True 跑，多个请求可能并发进来。
如果所有线程共用一条连接，MySQL 的报文序号会错乱
（Packet sequence number wrong），严重时直接把进程打崩，
所以这里按「线程 + 库」各持一条连接。
"""
import datetime
import decimal
import json
import threading

import pymysql
from pymysql.cursors import DictCursor

from config import MYSQL, DB_DEMO, DB_REAL

_local = threading.local()


def _new_conn(db):
    return pymysql.connect(database=db, cursorclass=DictCursor,
                           autocommit=True, **MYSQL)


def conn(db):
    """当前线程在指定库上的连接；不存在或已断开就重连"""
    pool = getattr(_local, "pool", None)
    if pool is None:
        pool = {}
        _local.pool = pool
    c = pool.get(db)
    if c is not None:
        try:
            c.ping(reconnect=True)
            return c
        except Exception:
            try:
                c.close()
            except Exception:
                pass
    c = _new_conn(db)
    pool[db] = c
    return c


def real():
    return conn(DB_REAL)


def demo():
    return conn(DB_DEMO)


def query(db, sql, args=None):
    cur = conn(db).cursor()
    try:
        cur.execute(sql, args or ())
        return cur.fetchall()
    finally:
        cur.close()


def one(db, sql, args=None):
    rows = query(db, sql, args)
    return rows[0] if rows else None


def scalar(db, sql, args=None):
    r = one(db, sql, args)
    return list(r.values())[0] if r else None


def execute(db, sql, args=None):
    cur = conn(db).cursor()
    try:
        return cur.execute(sql, args or ())
    finally:
        cur.close()


class JSONEncoder(json.JSONEncoder):
    """把 Decimal / date / datetime / bytes 转成 JSON 友好类型"""
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        if isinstance(o, (datetime.datetime, datetime.date)):
            return o.strftime("%Y-%m-%d %H:%M:%S") if isinstance(o, datetime.datetime) else o.strftime("%Y-%m-%d")
        if isinstance(o, (bytes, bytearray)):
            return o.decode("utf-8", "replace")
        if isinstance(o, set):
            return list(o)
        return super().default(o)


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, cls=JSONEncoder)
