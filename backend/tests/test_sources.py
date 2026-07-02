"""/api/v1/sources の現状挙動を固定する characterization test。"""
from api_helpers import register_source


def test_register_source_returns_created_source(client):
    body = register_source(client, "bookmeter", "読書メーター")
    assert body["slug"] == "bookmeter"
    assert body["display_name"] == "読書メーター"
    assert body["active"] is True
    assert body["description"] is None
    assert body["id"] == 1
    # 一覧用の集計フィールドは register のレスポンスでは常に None
    assert body["last_update_at"] is None
    assert body["representative_url"] is None


def test_register_duplicate_slug_conflicts(client):
    register_source(client, "bookmeter")
    res = client.post("/api/v1/sources/register", json={"slug": "bookmeter", "display_name": "x"})
    assert res.status_code == 409
    assert "already registered" in res.json()["detail"]


def test_register_invalid_slug_rejected(client):
    # slug は ^[a-z0-9_-]+$ のみ許容
    res = client.post("/api/v1/sources/register", json={"slug": "Bad Slug!", "display_name": "x"})
    assert res.status_code == 422


def test_list_sources_empty(client):
    assert client.get("/api/v1/sources").json() == []


def test_list_sources_without_records_has_null_aggregates(client):
    register_source(client, "bookmeter")
    rows = client.get("/api/v1/sources").json()
    assert len(rows) == 1
    assert rows[0]["last_update_at"] is None
    assert rows[0]["representative_url"] is None


def test_list_sources_aggregates_last_update_and_representative_url(client):
    register_source(client, "filmarks", "Filmarks")
    res = client.post("/api/v1/ingest/events", json={"records": [
        {
            "source_slug": "filmarks",
            "external_id": "fm_1",
            "record_type": "movie",
            "title": "映画A",
            "payload": {"source_url": "https://filmarks.com/movies/1"},
        },
    ]})
    assert res.status_code == 202

    rows = client.get("/api/v1/sources").json()
    assert rows[0]["last_update_at"] is not None
    assert rows[0]["representative_url"] == "https://filmarks.com/movies/1"


def test_representative_url_ignores_records_without_source_url(client):
    register_source(client, "studyplus", "Studyplus")
    client.post("/api/v1/ingest/events", json={"records": [
        {"source_slug": "studyplus", "external_id": "sp_1", "record_type": "study",
         "payload": {"minutes": 30}},
    ]})
    rows = client.get("/api/v1/sources").json()
    assert rows[0]["last_update_at"] is not None
    assert rows[0]["representative_url"] is None


def test_list_sources_ordered_by_id(client):
    register_source(client, "b-source")
    register_source(client, "a-source")
    rows = client.get("/api/v1/sources").json()
    assert [r["slug"] for r in rows] == ["b-source", "a-source"]
