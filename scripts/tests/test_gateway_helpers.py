"""スクリプト間で重複している gateway/state ヘルパーの characterization test。

共通モジュールへ抽出する前提として、各実装の現状挙動
（load_api_key のエラー処理の違いを含む）を固定する。
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import filmarks_sync_delta as delta
import studyplus_sync as sp


# ── load_api_key ──────────────────────────────────────────────────────────────

def test_load_api_key_reads_env_file(tmp_path):
    (tmp_path / ".env").write_text("FOO=bar\nGATEWAY_API_KEY=secret-123\n")
    assert delta.load_api_key(tmp_path) == "secret-123"
    assert sp.load_api_key(tmp_path) == "secret-123"


def test_load_api_key_filmarks_returns_empty_when_missing(tmp_path):
    # filmarks/bookmeter 系は .env やキーが無ければ空文字（認証なしモード）
    assert delta.load_api_key(tmp_path) == ""
    (tmp_path / ".env").write_text("OTHER=1\n")
    assert delta.load_api_key(tmp_path) == ""


def test_load_api_key_studyplus_raises_when_missing(tmp_path):
    # studyplus 版だけはエラーにする（挙動差をここで明示的に固定）
    with pytest.raises(RuntimeError):
        sp.load_api_key(tmp_path)
    (tmp_path / ".env").write_text("OTHER=1\n")
    with pytest.raises(RuntimeError):
        sp.load_api_key(tmp_path)


# ── load_state / save_state ──────────────────────────────────────────────────

@pytest.mark.parametrize("mod", [delta, sp])
def test_load_state_default_when_missing(mod, tmp_path):
    state = mod.load_state(tmp_path / "nope.json")
    assert state == {"known_external_ids": [], "last_run_at": None}


@pytest.mark.parametrize("mod", [delta, sp])
def test_load_state_default_when_corrupt(mod, tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{broken json")
    assert mod.load_state(p) == {"known_external_ids": [], "last_run_at": None}


@pytest.mark.parametrize("mod", [delta, sp])
def test_save_and_load_state_roundtrip(mod, tmp_path):
    p = tmp_path / "deep" / "dir" / "state.json"  # 親ディレクトリも作られる
    state = {"known_external_ids": ["a", "b"], "last_run_at": "2026-07-02T00:00:00+00:00"}
    mod.save_state(p, state)
    assert mod.load_state(p) == state


# ── gateway_request ───────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):
    def _respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode() if length else ""
        echo = {
            "method": self.command,
            "path": self.path,
            "auth": self.headers.get("Authorization"),
            "body": json.loads(body) if body else None,
        }
        data = json.dumps(echo).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = _respond
    do_POST = _respond

    def log_message(self, *args):
        pass


@pytest.fixture
def echo_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.mark.parametrize("mod", [delta, sp])
def test_gateway_request_get(mod, echo_server):
    code, body = mod.gateway_request(echo_server, "/api/v1/sources")
    assert code == 200
    assert body["method"] == "GET"
    assert body["path"] == "/api/v1/sources"
    assert body["auth"] is None


@pytest.mark.parametrize("mod", [delta, sp])
def test_gateway_request_post_with_api_key(mod, echo_server):
    code, body = mod.gateway_request(
        echo_server + "/",  # 末尾スラッシュは除去される
        "/api/v1/ingest/events",
        method="POST",
        payload={"records": [{"title": "日本語"}]},
        api_key="k1",
    )
    assert code == 200
    assert body["method"] == "POST"
    assert body["auth"] == "Bearer k1"
    assert body["body"] == {"records": [{"title": "日本語"}]}
