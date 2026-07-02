"""backend API テスト共通ヘルパー。

conftest.py に置くと scripts/tests/conftest.py とモジュール名が衝突して
ルートからの一括実行 (pytest backend/tests scripts/tests) が壊れるため、
一意な名前のモジュールに分離している。
"""
from fastapi.testclient import TestClient


def register_source(client: TestClient, slug: str = "bookmeter", display_name: str = "読書メーター") -> dict:
    res = client.post("/api/v1/sources/register", json={"slug": slug, "display_name": display_name})
    assert res.status_code == 201, res.text
    return res.json()
