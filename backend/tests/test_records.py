"""/api/v1/records の現状挙動を固定する characterization test。"""
from datetime import datetime, timedelta, timezone

from conftest import register_source


def _seed(client, slug="bookmeter", n=3):
    register_source(client, slug)
    records = [
        {"source_slug": slug, "external_id": f"e{i}", "record_type": "book", "title": f"本{i}"}
        for i in range(n)
    ]
    res = client.post("/api/v1/ingest/events", json={"records": records})
    assert res.status_code == 202


def test_list_records_empty(client):
    assert client.get("/api/v1/records").json() == []


def test_filter_by_source_slug(client):
    _seed(client, "bookmeter", 2)
    _seed(client, "filmarks", 1)
    rows = client.get("/api/v1/records", params={"source": "bookmeter"}).json()
    assert len(rows) == 2


def test_unknown_source_slug_returns_empty_list(client):
    _seed(client)
    # 存在しない slug は 404 ではなく空リスト
    assert client.get("/api/v1/records", params={"source": "nope"}).json() == []


def test_limit_capped_at_500(client):
    res = client.get("/api/v1/records", params={"limit": 501})
    assert res.status_code == 422


def test_limit_applies(client):
    _seed(client, n=5)
    rows = client.get("/api/v1/records", params={"limit": 2}).json()
    assert len(rows) == 2


def test_from_to_filter_on_ingested_at(client):
    _seed(client, n=1)
    now = datetime.now(timezone.utc)
    future = (now + timedelta(days=1)).isoformat()
    past = (now - timedelta(days=1)).isoformat()

    assert len(client.get("/api/v1/records", params={"from": past}).json()) == 1
    assert client.get("/api/v1/records", params={"from": future}).json() == []
    assert client.get("/api/v1/records", params={"to": past}).json() == []


def test_response_includes_payload(client):
    register_source(client, "studyplus")
    client.post("/api/v1/ingest/events", json={"records": [
        {"source_slug": "studyplus", "external_id": "d1", "record_type": "study",
         "payload": {"minutes": 45}},
    ]})
    rows = client.get("/api/v1/records").json()
    assert rows[0]["payload"] == {"minutes": 45}
