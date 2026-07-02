"""backend API の characterization test 用フィクスチャ。

DB_PATH はモジュール import 前に一時ファイルへ向ける必要がある
(app.database が import 時に engine を構築するため)。
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

_tmpdir = tempfile.mkdtemp(prefix="sync-gateway-test-")
os.environ["DB_PATH"] = os.path.join(_tmpdir, "test.db")
os.environ.pop("GATEWAY_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """テストごとに全テーブルを作り直して独立性を保つ。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_key(monkeypatch):
    """認証を有効化し、そのキーを返す。"""
    monkeypatch.setenv("GATEWAY_API_KEY", "test-secret-key")
    return "test-secret-key"


def register_source(client: TestClient, slug: str = "bookmeter", display_name: str = "読書メーター") -> dict:
    res = client.post("/api/v1/sources/register", json={"slug": slug, "display_name": display_name})
    assert res.status_code == 201, res.text
    return res.json()
