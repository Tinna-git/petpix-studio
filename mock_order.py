# -*- coding: utf-8 -*-
"""PetPix Studio — 内存 Mock 订单系统"""

import time
import uuid
from datetime import datetime

PRICING = [
    {"id": "trial",     "name": "体验版",     "desc": "3张精修带水印",           "price": 9.9,  "original": 19.9},
    {"id": "portrait",  "name": "写真套系",   "desc": "10张精修3风格",          "price": 29,   "original": 59},
    {"id": "guardian",  "name": "守护神套系", "desc": "5张守护神+3张合影",      "price": 49,   "original": 99},
    {"id": "premium",   "name": "全能礼包",   "desc": "写真10+守护神5+合影3",   "price": 79,   "original": 159},
]

PRICE_MAP = {p["id"]: p for p in PRICING}

_orders: dict = {}


def create_order(package_id: str, style_id: str = "", user_note: str = "") -> dict:
    if package_id not in PRICE_MAP:
        return {"error": "未知套系"}
    pkg = PRICE_MAP[package_id]
    order_id = f"PP{uuid.uuid4().hex[:16].upper()}"
    order = {
        "order_id": order_id,
        "package_id": package_id,
        "package_name": pkg["name"],
        "style_id": style_id,
        "amount": pkg["price"],
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "paid_at": None,
    }
    _orders[order_id] = order
    return {"order_id": order_id, "amount": pkg["price"], "status": "pending"}


def pay_order(order_id: str, method: str = "wechat") -> dict:
    order = _orders.get(order_id)
    if not order:
        return {"error": "订单不存在"}
    if order["status"] == "paid":
        return {"order_id": order_id, "status": "paid"}
    order["status"] = "paid"
    order["pay_method"] = method
    order["paid_at"] = datetime.now().isoformat()
    return {"order_id": order_id, "status": "paid", "amount": order["amount"]}


def get_order(order_id: str) -> dict:
    return _orders.get(order_id, {"error": "订单不存在"})


def list_orders() -> list:
    return sorted(_orders.values(), key=lambda o: o["created_at"], reverse=True)


def create_share_link(order_id: str) -> dict:
    order = _orders.get(order_id)
    if not order:
        return {"error": "订单不存在"}
    link = f"https://petpix.studio/share/{order_id[:8]}"
    return {"share_url": link, "order_id": order_id}
