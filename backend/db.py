# -*- coding: utf-8 -*-
"""MySQL 连接与查询helper"""
import datetime
import decimal
import json

import pymysql
from pymysql.cursors import DictCursor

from config import MYSQL, DB_DEMO, DB_REAL

_pool = {}


def conn(db):
    """每个库一个长连接（Flask 单进程够用；生产换连接池）"""
    c = _pool.get(db)
    if c is None:
        c = pymysql.connect(database=db, cursorclass=DictCursor,
                            autocommit=True, **MYSQL)
        _pool[db] = c
    else:
        try:
            c.ping(reconnect=True)
        except Exception:
            c = pymysql.connect(database=db, cursorclass=DictCursor,
                                autocommit=True, **MYSQL)
            _pool[db] = c
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
