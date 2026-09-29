from fastapi.testclient import TestClient

from app import app


client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer demo-inventory-token"}


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_inventory_query_normalizes_sku() -> None:
    response = client.get("/api/v1/inventory/a001", headers=AUTH_HEADERS)

    assert response.status_code == 200
    assert response.json()["sku"] == "A001"
    assert response.json()["available_stock"] == 23
    assert response.json()["stock_status"] == "有货"


def test_inventory_query_requires_token() -> None:
    response = client.get("/api/v1/inventory/A001")

    assert response.status_code == 401
    assert response.json()["detail"] == "无效或缺失的访问令牌"


def test_inventory_query_returns_not_found() -> None:
    response = client.get("/api/v1/inventory/UNKNOWN", headers=AUTH_HEADERS)

    assert response.status_code == 404
    assert response.json()["detail"] == "未找到 SKU UNKNOWN"


def test_demo_page_shows_order_decisions() -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "S1001" in response.text
    assert "可发货" in response.text
    assert "缺货待回复" in response.text
    assert "无此SKU" in response.text
    assert "不承诺" in response.text


def test_demo_page_shows_order_decisions() -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    assert "S1001" in response.text
    assert "可发货" in response.text
    assert "缺货待回复" in response.text
    assert "无此SKU" in response.text
    assert "不承诺" in response.text
