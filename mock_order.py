# -*- coding: utf-8 -*-
"""PetPix Studio — SQLite 订单持久化系统"""

import os
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

PRICING = [
    {"id": "trial",     "name": "体验版",     "desc": "3张精修带水印",           "price": 9.9,  "original": 19.9},
    {"id": "portrait",  "name": "写真套系",   "desc": "10张精修3风格",          "price": 29,   "original": 59},
    {"id": "guardian",  "name": "守护神套系", "desc": "5张守护神+3张合影",      "price": 49,   "original": 99},
    {"id": "premium",   "name": "全能礼包",   "desc": "写真10+守护神5+合影3",   "price": 79,   "original": 159},
]

PRICE_MAP = {p["id"]: p for p in PRICING}

# 数据库路径 — 环境变量指定或默认项目根目录
DB_PATH = Path(os.environ.get("DB_PATH", str(Path(__file__).parent / "petpix.db")))


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（autocommit off, 行工厂 dict）"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化数据库表（幂等）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id       TEXT PRIMARY KEY,
            package_id     TEXT NOT NULL,
            package_name   TEXT NOT NULL,
            style_id       TEXT DEFAULT '',
            style_name     TEXT DEFAULT '',
            amount         REAL NOT NULL,
            status         TEXT DEFAULT 'pending',
            image_url      TEXT DEFAULT '',
            pay_method     TEXT DEFAULT '',
            user_note      TEXT DEFAULT '',
            created_at     TEXT NOT NULL,
            paid_at        TEXT DEFAULT NULL,
            share_code     TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS generations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id       TEXT,
            style_id       TEXT NOT NULL,
            image_url      TEXT DEFAULT '',
            filename       TEXT DEFAULT '',
            source_file    TEXT DEFAULT '',
            mock           INTEGER DEFAULT 0,
            created_at     TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );

        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
        CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at);
        CREATE INDEX IF NOT EXISTS idx_generations_order ON generations(order_id);
    """)
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转为普通 dict（None 值保留）"""
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


# ── 订单 CRUD ──

def create_order(package_id: str, style_id: str = "", user_note: str = "", image_url: str = "") -> dict:
    if package_id not in PRICE_MAP:
        return {"error": "未知套系"}
    pkg = PRICE_MAP[package_id]
    order_id = f"PP{uuid.uuid4().hex[:16].upper()}"
    now = datetime.now().isoformat()

    conn = _get_conn()
    try:
        conn.execute(
            """INSERT INTO orders (order_id, package_id, package_name, style_id, amount, status, image_url, user_note, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
            (order_id, package_id, pkg["name"], style_id, pkg["price"], image_url, user_note, now),
        )
        conn.commit()
    finally:
        conn.close()

    return {"order_id": order_id, "amount": pkg["price"], "status": "pending"}


def pay_order(order_id: str, method: str = "wechat") -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": "订单不存在"}
        if row["status"] == "paid":
            return {"order_id": order_id, "status": "paid"}

        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE orders SET status='paid', pay_method=?, paid_at=? WHERE order_id=?",
            (method, now, order_id),
        )
        conn.commit()
    finally:
        conn.close()

    return {"order_id": order_id, "status": "paid", "amount": row["amount"]}


def get_order(order_id: str) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": "订单不存在"}
        return _row_to_dict(row)
    finally:
        conn.close()


def list_orders() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def update_order_style_name(order_id: str, style_name: str):
    """补充 style_name（由 server.py 调用）"""
    conn = _get_conn()
    try:
        conn.execute("UPDATE orders SET style_name=? WHERE order_id=?", (style_name, order_id))
        conn.commit()
    finally:
        conn.close()


# ── 生成记录 ──

def save_generation(style_id: str, filename: str, image_url: str = "", source_file: str = "", mock: bool = False, order_id: str = "") -> int:
    """保存一次生成记录，返回记录 id"""
    conn = _get_conn()
    try:
        cur = conn.execute(
            """INSERT INTO generations (order_id, style_id, image_url, filename, source_file, mock, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (order_id, style_id, image_url, filename, source_file, 1 if mock else 0, datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_generations(limit: int = 20) -> list:
    """列出最近的生成记录"""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM generations ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ── 分享 ──

def create_share_link(order_id: str) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
        if not row:
            return {"error": "订单不存在"}

        # 生成唯一分享码
        share_code = uuid.uuid4().hex[:8]
        conn.execute("UPDATE orders SET share_code=? WHERE order_id=?", (share_code, order_id))
        conn.commit()

        link = f"https://petpix.studio/share/{share_code}"
        return {"share_url": link, "order_id": order_id}
    finally:
        conn.close()


# ── 统计 ──

def get_stats() -> dict:
    """获取全局统计数据"""
    conn = _get_conn()
    try:
        total_orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        paid_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status='paid'").fetchone()[0]
        total_revenue = conn.execute("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='paid'").fetchone()[0]
        total_generations = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
        mock_count = conn.execute("SELECT COUNT(*) FROM generations WHERE mock=1").fetchone()[0]
        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "total_revenue": round(total_revenue, 2),
            "total_generations": total_generations,
            "real_generations": total_generations - mock_count,
        }
    finally:
        conn.close()
