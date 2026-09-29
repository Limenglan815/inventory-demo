# 电商库存与售后演示

模拟库存，不连接真实 ERP。用 Dify 的 HTTP 节点可以调用本接口。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --reload
```

- 接口文档：http://127.0.0.1:8000/docs
- 演示页：http://127.0.0.1:8000/demo
- 请求头：`Authorization: Bearer demo-inventory-token`

可查询的 SKU：`A001` 有货，`A002` 缺货，`A003` 有货。

## 测试

```powershell
pytest
```
