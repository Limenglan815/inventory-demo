from workflow import ACTION_CAN_SHIP, ACTION_SHORT, ACTION_UNKNOWN, Order, render_demo_html, summarize_orders


INVENTORY = {
    "A001": {
        "product_name": "星月银色项链",
        "available_stock": 23,
        "locked_stock": 4,
        "warehouse": "深圳一号仓",
    },
    "A002": {
        "product_name": "山茶花耳钉",
        "available_stock": 0,
        "locked_stock": 0,
        "warehouse": "深圳一号仓",
    },
    "A003": {
        "product_name": "简约开口戒指",
        "available_stock": 7,
        "locked_stock": 2,
        "warehouse": "东莞二号仓",
    },
}


def test_summary_splits_ship_stock_and_unknown_sku() -> None:
    orders = [
        Order("S1001", "A001", 1, "When will this ship to the US?", "Amazon"),
        Order("S1002", "A002", 1, "Do you still have this in stock?", "Shopify"),
        Order("S1003", "A003", 10, "需要 10 件", "独立站"),
        Order("S1004", "A001", 2, "可以发到德国吗？", "独立站"),
        Order("S1005", "B999", 1, "请确认货号", "Amazon"),
    ]

    summary = summarize_orders(orders, INVENTORY)
    by_id = {row["order_id"]: row for row in summary["rows"]}

    assert by_id["S1001"]["action"] == ACTION_CAN_SHIP
    assert "美国" in by_id["S1001"]["reply_zh"]
    assert "date" in by_id["S1001"]["reply_en"]
    assert by_id["S1002"]["action"] == "缺货待回复"
    assert by_id["S1003"]["action"] == ACTION_SHORT
    assert "7" in by_id["S1003"]["reply_zh"]
    assert "德国" in by_id["S1004"]["reply_zh"]
    assert by_id["S1005"]["action"] == ACTION_UNKNOWN
    assert summary["counts"][ACTION_CAN_SHIP] == 2
    assert [item["sku"] for item in summary["listings"]] == ["A001"]


def test_demo_html_escapes_customer_message() -> None:
    orders = [Order("S9", "A001", 1, "<script>alert(1)</script>", "Amazon")]

    page = render_demo_html(summarize_orders(orders, INVENTORY))

    assert "<script>" not in page
    assert "&lt;script&gt;" in page
