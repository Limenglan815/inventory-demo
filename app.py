import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from workflow import load_orders, render_demo_html, summarize_orders


app = FastAPI(
    title="电商库存模拟接口",
    description="用于演示 Dify 调用 ERP 库存查询接口。",
    version="1.0.0",
)

API_TOKEN = os.getenv("INVENTORY_API_TOKEN", "demo-inventory-token")
bearer_scheme = HTTPBearer(auto_error=False)
ORDERS_PATH = Path(__file__).resolve().parent / "data" / "orders.csv"

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


class InventoryResponse(BaseModel):
    sku: str
    product_name: str
    available_stock: int
    locked_stock: int
    warehouse: str
    stock_status: str
    updated_at: datetime


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> None:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or credentials.credentials != API_TOKEN
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或缺失的访问令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/demo", response_class=HTMLResponse)
def demo_page() -> str:
    summary = summarize_orders(load_orders(ORDERS_PATH), INVENTORY)
    return render_demo_html(summary)


@app.get(
    "/api/v1/inventory/{sku}",
    response_model=InventoryResponse,
    dependencies=[Depends(verify_token)],
)
def get_inventory(sku: str) -> InventoryResponse:
    normalized_sku = sku.strip().upper()
    item = INVENTORY.get(normalized_sku)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到 SKU {normalized_sku}",
        )

    available_stock = item["available_stock"]
    return InventoryResponse(
        sku=normalized_sku,
        product_name=item["product_name"],
        available_stock=available_stock,
        locked_stock=item["locked_stock"],
        warehouse=item["warehouse"],
        stock_status="有货" if available_stock > 0 else "缺货",
        updated_at=datetime.now(timezone.utc),
    )
