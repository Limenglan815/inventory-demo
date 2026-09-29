import csv
import html
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


ENGLISH_NAMES = {
    "A001": "star-and-moon silver-tone necklace",
    "A002": "camellia stud earrings",
    "A003": "simple open ring",
}

ACTION_CAN_SHIP = "可发货"
ACTION_OUT_OF_STOCK = "缺货待回复"
ACTION_SHORT = "库存不足"
ACTION_UNKNOWN = "无此SKU"
ACTION_BAD_QTY = "数量无效"


@dataclass(frozen=True)
class Order:
    order_id: str
    sku: str
    quantity: int
    customer_message: str
    channel: str


def load_orders(path: Path) -> list[Order]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            Order(
                order_id=row["order_id"].strip(),
                sku=row["sku"].strip().upper(),
                quantity=int(row["quantity"]),
                customer_message=row["customer_message"].strip(),
                channel=row["channel"].strip(),
            )
            for row in reader
        ]


def summarize_orders(orders: list[Order], inventory: dict) -> dict:
    rows = [_build_row(order, inventory.get(order.sku)) for order in orders]
    counts = {action: 0 for action in (
        ACTION_CAN_SHIP,
        ACTION_OUT_OF_STOCK,
        ACTION_SHORT,
        ACTION_UNKNOWN,
        ACTION_BAD_QTY,
    )}
    for row in rows:
        counts[row["action"]] += 1

    listings = []
    seen = set()
    for row in rows:
        if row["action"] != ACTION_CAN_SHIP or row["sku"] in seen:
            continue
        seen.add(row["sku"])
        listings.append(
            {
                "sku": row["sku"],
                "listing_zh": f"{row['product_name']}。{row['warehouse']}现货可发。",
                "listing_en": (
                    f"{row['english_name']}. In stock at {row['warehouse']} "
                    "and ready to ship."
                ),
            }
        )

    return {"counts": counts, "rows": rows, "listings": listings}


def _build_row(order: Order, item: Optional[dict]) -> dict:
    english_name = ENGLISH_NAMES.get(order.sku, order.sku)
    if order.quantity < 1:
        return _row(
            order,
            product_name="—",
            english_name=english_name,
            available_stock=None,
            warehouse="—",
            action=ACTION_BAD_QTY,
            reply_zh=f"订单 {order.order_id} 的数量无效，先不要处理发货。",
            reply_en=(
                f"Order {order.order_id} has an invalid quantity. "
                "Do not ship it."
            ),
        )

    if item is None:
        return _row(
            order,
            product_name="—",
            english_name=english_name,
            available_stock=None,
            warehouse="—",
            action=ACTION_UNKNOWN,
            reply_zh=(
                f"订单 {order.order_id} 的货号 {order.sku} 在库存里不存在，"
                "请核对后再处理。"
            ),
            reply_en=(
                f"Order {order.order_id}: item code {order.sku} is not in "
                "the inventory. Please check the code."
            ),
        )

    product_name = item["product_name"]
    english_name = ENGLISH_NAMES.get(order.sku, product_name)
    available = item["available_stock"]
    warehouse = item["warehouse"]

    if available <= 0:
        return _row(
            order,
            product_name=product_name,
            english_name=english_name,
            available_stock=available,
            warehouse=warehouse,
            action=ACTION_OUT_OF_STOCK,
            reply_zh=(
                f"{product_name}（{order.sku}）现在没有现货，这单先不要发。"
                "到货后可以再通知客户。不承诺具体日期。"
            ),
            reply_en=(
                f"{english_name} ({order.sku}) are out of stock. "
                "Do not ship this order. Message the customer when it is back. "
                "Do not promise a date."
            ),
        )

    if order.quantity > available:
        return _row(
            order,
            product_name=product_name,
            english_name=english_name,
            available_stock=available,
            warehouse=warehouse,
            action=ACTION_SHORT,
            reply_zh=(
                f"{product_name}（{order.sku}）现货只有 {available} 件，"
                f"订单要 {order.quantity} 件，暂时不能按这个数量发货。"
                f"可以改成 {available} 件，或等补货。不承诺到货日期。"
            ),
            reply_en=(
                f"{english_name} ({order.sku}): only {available} are in stock, "
                f"and this order asks for {order.quantity}. "
                "We cannot ship the full quantity. "
                f"The order can be changed to {available}, or wait for restock. "
                "Do not promise a date."
            ),
        )

    destination = _destination_sentence(order.customer_message)
    return _row(
        order,
        product_name=product_name,
        english_name=english_name,
        available_stock=available,
        warehouse=warehouse,
        action=ACTION_CAN_SHIP,
        reply_zh=(
            f"{product_name}（{order.sku}）现货 {available} 件，"
            f"这单 {order.quantity} 件可以从{warehouse}发。"
            f"{destination['zh']}"
        ),
        reply_en=(
            f"{english_name} ({order.sku}): {available} in stock. "
            f"This order of {order.quantity} can ship from {warehouse}. "
            f"{destination['en']}"
        ),
    )


def _destination_sentence(message: str) -> dict[str, str]:
    text = message.lower()
    if "德国" in message or "germany" in text:
        return {
            "zh": "可以发德国。运费和时效以下单页面为准，这里不承诺具体日期。",
            "en": "It can ship to Germany. Freight and delivery time are on the checkout page. Do not promise a date.",
        }
    if "美国" in message or " us" in f" {text}" or "u.s" in text:
        return {
            "zh": "可以发美国。运费和时效以下单页面为准，这里不承诺具体日期。",
            "en": "It can ship to the US. Freight and delivery time are on the checkout page. Do not promise a date.",
        }
    return {
        "zh": "运费和时效以下单页面为准，这里不承诺具体日期。",
        "en": "Freight and delivery time are on the checkout page. Do not promise a date.",
    }


def _row(
    order: Order,
    product_name: str,
    english_name: str,
    available_stock: Optional[int],
    warehouse: str,
    action: str,
    reply_zh: str,
    reply_en: str,
) -> dict:
    return {
        "order_id": order.order_id,
        "sku": order.sku,
        "quantity": order.quantity,
        "customer_message": order.customer_message,
        "channel": order.channel,
        "product_name": product_name,
        "english_name": english_name,
        "available_stock": available_stock,
        "warehouse": warehouse,
        "action": action,
        "reply_zh": reply_zh,
        "reply_en": reply_en,
    }


def render_demo_html(summary: dict) -> str:
    counts = summary["counts"]
    rows_html = "\n".join(_render_row(row) for row in summary["rows"])
    listings_html = "\n".join(
        (
            "<article class='card'>"
            f"<h3>{html.escape(item['sku'])}</h3>"
            f"<p>{html.escape(item['listing_zh'])}</p>"
            f"<p class='en'>{html.escape(item['listing_en'])}</p>"
            "</article>"
        )
        for item in summary["listings"]
    )
    if not listings_html:
        listings_html = "<p>当前没有可发货的商品。</p>"

    count_html = "\n".join(
        f"<li><span>{html.escape(name)}</span><strong>{count}</strong></li>"
        for name, count in counts.items()
    )
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>跨境订单处理演示</title>
  <style>
    body {{ margin: 0; font-family: "Segoe UI", sans-serif; background: #f4f6f8; color: #1c2430; }}
    main {{ max-width: 980px; margin: 0 auto; padding: 28px 20px 48px; }}
    h1 {{ font-size: 28px; margin-bottom: 8px; }}
    .note {{ color: #526072; line-height: 1.5; }}
    ul.counts {{ display: flex; flex-wrap: wrap; gap: 10px; padding: 0; list-style: none; }}
    ul.counts li {{ background: #fff; border-radius: 10px; padding: 12px 14px; min-width: 120px; }}
    ul.counts span {{ display: block; color: #526072; font-size: 13px; }}
    ul.counts strong {{ font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e6ebf0; vertical-align: top; font-size: 14px; }}
    th {{ background: #e8eef5; }}
    .cards {{ display: grid; gap: 12px; }}
    .card {{ background: #fff; border-radius: 12px; padding: 14px 16px; }}
    .en {{ color: #274690; }}
    h2 {{ margin-top: 28px; font-size: 20px; }}
  </style>
</head>
<body>
  <main>
    <h1>跨境订单处理演示</h1>
    <p class="note">演示数据，不是真实 ERP。先查库存，再按客户留言里的目的地选句子。没有调用外部模型，也不承诺到货日期。</p>
    <ul class="counts">
      {count_html}
    </ul>
    <h2>订单</h2>
    <table>
      <thead>
        <tr>
          <th>订单</th>
          <th>货号</th>
          <th>数量</th>
          <th>现货</th>
          <th>处理</th>
          <th>客户留言</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    <h2>回复草稿</h2>
    <div class="cards">
      {"".join(_render_reply(row) for row in summary["rows"])}
    </div>
    <h2>可发货商品的上架短句</h2>
    <div class="cards">
      {listings_html}
    </div>
  </main>
</body>
</html>
"""


def _render_row(row: dict) -> str:
    available = "—" if row["available_stock"] is None else str(row["available_stock"])
    return (
        "<tr>"
        f"<td>{html.escape(row['order_id'])}</td>"
        f"<td>{html.escape(row['sku'])}</td>"
        f"<td>{row['quantity']}</td>"
        f"<td>{html.escape(available)}</td>"
        f"<td>{html.escape(row['action'])}</td>"
        f"<td>{html.escape(row['customer_message'])}</td>"
        "</tr>"
    )


def _render_reply(row: dict) -> str:
    return (
        "<article class='card'>"
        f"<h3>{html.escape(row['order_id'])} · {html.escape(row['action'])}</h3>"
        f"<p>{html.escape(row['reply_zh'])}</p>"
        f"<p class='en'>{html.escape(row['reply_en'])}</p>"
        "</article>"
    )
