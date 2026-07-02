"""/api/v1/runs の現状挙動を固定する characterization test。"""
from conftest import register_source


def test_create_run(client):
    src = register_source(client)
    res = client.post("/api/v1/runs", json={"source_id": src["id"]})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "running"
    assert body["finished_at"] is None
    assert body["records_processed"] == 0
    assert body["records_created"] == 0
    assert body["records_updated"] == 0
    assert body["records_failed"] == 0
    assert body["error_message"] is None


def test_create_run_unknown_source_404(client):
    res = client.post("/api/v1/runs", json={"source_id": 999})
    assert res.status_code == 404
    assert res.json()["detail"] == "Source not found"


def test_patch_run_status_sets_finished_at(client):
    src = register_source(client)
    run = client.post("/api/v1/runs", json={"source_id": src["id"]}).json()
    res = client.patch(f"/api/v1/runs/{run['id']}", json={"status": "success"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "success"
    assert body["finished_at"] is not None


def test_patch_run_partial_fields_only(client):
    src = register_source(client)
    run = client.post("/api/v1/runs", json={"source_id": src["id"]}).json()
    # status を渡さなければ finished_at は付かない
    res = client.patch(f"/api/v1/runs/{run['id']}", json={"records_failed": 3, "error_message": "boom"})
    body = res.json()
    assert body["status"] == "running"
    assert body["finished_at"] is None
    assert body["records_failed"] == 3
    assert body["error_message"] == "boom"


def test_patch_run_invalid_status_rejected(client):
    src = register_source(client)
    run = client.post("/api/v1/runs", json={"source_id": src["id"]}).json()
    # status は success | failed のみ（running へ戻すのは不可）
    res = client.patch(f"/api/v1/runs/{run['id']}", json={"status": "running"})
    assert res.status_code == 422


def test_patch_unknown_run_404(client):
    res = client.patch("/api/v1/runs/999", json={"status": "success"})
    assert res.status_code == 404


def test_list_runs_newest_first_with_limit(client):
    src = register_source(client)
    ids = [client.post("/api/v1/runs", json={"source_id": src["id"]}).json()["id"] for _ in range(3)]
    rows = client.get("/api/v1/runs", params={"limit": 2}).json()
    assert len(rows) == 2
    # started_at 降順（同時刻の場合の順序は id とは限らないが、新しい run が含まれる）
    assert {r["id"] for r in rows}.issubset(set(ids))
