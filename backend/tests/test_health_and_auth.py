"""/healthz と Bearer 認証の現状挙動を固定する characterization test。"""
from api_helpers import register_source


def test_healthz(client):
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_auth_disabled_when_key_not_configured(client):
    # GATEWAY_API_KEY 未設定なら書き込み系もトークンなしで通る（MVP互換）
    res = client.post("/api/v1/sources/register", json={"slug": "s1", "display_name": "S1"})
    assert res.status_code == 201


def test_write_requires_token_when_key_configured(client, api_key):
    res = client.post("/api/v1/sources/register", json={"slug": "s1", "display_name": "S1"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Missing API key"


def test_wrong_token_rejected(client, api_key):
    res = client.post(
        "/api/v1/sources/register",
        json={"slug": "s1", "display_name": "S1"},
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid API key"


def test_correct_token_accepted(client, api_key):
    res = client.post(
        "/api/v1/sources/register",
        json={"slug": "s1", "display_name": "S1"},
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert res.status_code == 201


def test_non_bearer_scheme_rejected(client, api_key):
    res = client.post(
        "/api/v1/sources/register",
        json={"slug": "s1", "display_name": "S1"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert res.status_code == 401


def test_read_endpoints_do_not_require_token(client, api_key):
    # 読み取り系は認証対象外
    assert client.get("/api/v1/sources").status_code == 200
    assert client.get("/api/v1/runs").status_code == 200
    assert client.get("/api/v1/records").status_code == 200
    assert client.get("/healthz").status_code == 200
