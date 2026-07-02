"""/api/v1/ingest/events の現状挙動を固定する characterization test。

upsert・run 統計・auto-run 作成/確定など、このAPIの中核ロジックを対象とする。
"""
from api_helpers import register_source


def _ingest(client, records):
    res = client.post("/api/v1/ingest/events", json={"records": records})
    assert res.status_code == 202, res.text
    return res.json()


def _record(slug="bookmeter", **over):
    rec = {
        "source_slug": slug,
        "external_id": "ext-1",
        "record_type": "book",
        "title": "本A",
        "author": "著者A",
        "rating": 4.0,
        "status": "read",
        "payload": {"isbn": "123"},
    }
    rec.update(over)
    return rec


def test_ingest_creates_new_record(client):
    register_source(client)
    body = _ingest(client, [_record()])
    assert body == {"accepted": 1, "failed": 0, "errors": []}

    rows = client.get("/api/v1/records").json()
    assert len(rows) == 1
    r = rows[0]
    assert r["external_id"] == "ext-1"
    assert r["title"] == "本A"
    assert r["payload"] == {"isbn": "123"}


def test_ingest_unknown_source_slug_fails(client):
    body = _ingest(client, [_record(slug="nope")])
    assert body["accepted"] == 0
    assert body["failed"] == 1
    assert body["errors"] == ["Unknown source slug: nope"]
    assert client.get("/api/v1/records").json() == []


def test_ingest_upserts_by_source_and_external_id(client):
    register_source(client)
    _ingest(client, [_record()])
    _ingest(client, [_record(title="本A改", rating=5.0)])

    rows = client.get("/api/v1/records").json()
    assert len(rows) == 1  # 重複せず更新される
    assert rows[0]["title"] == "本A改"
    assert rows[0]["rating"] == 5.0


def test_ingest_update_keeps_existing_fields_when_none(client):
    register_source(client)
    _ingest(client, [_record()])
    # None のフィールドは既存値を保持する（Noneで上書きしない）
    _ingest(client, [_record(title=None, author=None, rating=None, status=None)])

    r = client.get("/api/v1/records").json()[0]
    assert r["title"] == "本A"
    assert r["author"] == "著者A"
    assert r["rating"] == 4.0
    assert r["status"] == "read"


def test_ingest_update_merges_payload_shallowly(client):
    register_source(client)
    _ingest(client, [_record(payload={"isbn": "123", "pages": 200})])
    _ingest(client, [_record(payload={"pages": 250, "note": "x"})])

    r = client.get("/api/v1/records").json()[0]
    assert r["payload"] == {"isbn": "123", "pages": 250, "note": "x"}


def test_ingest_empty_payload_keeps_existing_payload(client):
    register_source(client)
    _ingest(client, [_record()])
    _ingest(client, [_record(payload={})])
    r = client.get("/api/v1/records").json()[0]
    assert r["payload"] == {"isbn": "123"}


def test_ingest_without_external_id_always_creates(client):
    register_source(client)
    _ingest(client, [_record(external_id=None)])
    _ingest(client, [_record(external_id=None)])
    assert len(client.get("/api/v1/records").json()) == 2


def test_ingest_with_explicit_run_id_updates_stats(client):
    src = register_source(client)
    run = client.post("/api/v1/runs", json={"source_id": src["id"]}).json()

    _ingest(client, [
        _record(external_id="a", run_id=run["id"]),
        _record(external_id="b", run_id=run["id"]),
    ])
    _ingest(client, [_record(external_id="a", run_id=run["id"])])  # 2回目は update

    rows = client.get("/api/v1/runs").json()
    r = next(x for x in rows if x["id"] == run["id"])
    assert r["records_processed"] == 3
    assert r["records_created"] == 2
    assert r["records_updated"] == 1
    assert r["records_failed"] == 0
    # 明示 run_id の run は自動では finalize されない
    assert r["status"] == "running"
    assert r["finished_at"] is None


def test_ingest_without_run_id_auto_creates_and_finalizes_run(client):
    register_source(client)
    _ingest(client, [_record(external_id="a"), _record(external_id="b")])

    runs = client.get("/api/v1/runs").json()
    assert len(runs) == 1
    r = runs[0]
    assert r["status"] == "success"
    assert r["finished_at"] is not None
    assert r["records_processed"] == 2
    assert r["records_created"] == 2

    # レコードにも auto-run が紐づく
    for rec in client.get("/api/v1/records").json():
        assert rec["run_id"] == r["id"]


def test_ingest_auto_run_is_per_source_slug(client):
    register_source(client, "bookmeter")
    register_source(client, "filmarks")
    _ingest(client, [
        _record(slug="bookmeter", external_id="b1"),
        _record(slug="filmarks", external_id="f1", record_type="movie"),
    ])
    runs = client.get("/api/v1/runs").json()
    assert len(runs) == 2
    assert {r["source_id"] for r in runs} == {1, 2}


def test_ingest_unknown_slug_does_not_create_auto_run(client):
    _ingest(client, [_record(slug="nope")])
    assert client.get("/api/v1/runs").json() == []


def test_ingest_mixed_batch_continues_after_failure(client):
    register_source(client)
    body = _ingest(client, [
        _record(slug="nope", external_id="x"),
        _record(external_id="ok-1"),
    ])
    assert body["accepted"] == 1
    assert body["failed"] == 1
    assert len(client.get("/api/v1/records").json()) == 1


def test_ingest_empty_records_rejected(client):
    res = client.post("/api/v1/ingest/events", json={"records": []})
    assert res.status_code == 422


def test_ingest_rating_out_of_range_rejected(client):
    register_source(client)
    res = client.post("/api/v1/ingest/events", json={"records": [_record(rating=11)]})
    assert res.status_code == 422


def test_ingest_requires_api_key_when_configured(client, api_key):
    res = client.post("/api/v1/ingest/events", json={"records": [_record()]})
    assert res.status_code == 401
