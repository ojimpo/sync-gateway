"""同期スクリプト共通ヘルパー。

各同期スクリプトにコピペされていた gateway アクセス・.env 読み込み・
state 管理・HTMLテキスト処理をここに集約する。
"""
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── gateway ───────────────────────────────────────────────────────────────────

def gateway_request(base: str, path: str, method: str = "GET", payload=None, api_key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode() or "{}"
        return res.status, json.loads(body)


def load_api_key(repo_root: Path = REPO_ROOT, required: bool = False) -> str:
    """リポジトリ直下の .env から GATEWAY_API_KEY を読む。

    required=False では見つからなければ空文字（認証なしモード）。
    required=True では RuntimeError にする（studyplus 系の従来挙動）。
    """
    env = repo_root / ".env"
    if not env.exists():
        if required:
            raise RuntimeError(".env not found")
        return ""
    for line in env.read_text().splitlines():
        if line.startswith("GATEWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    if required:
        raise RuntimeError("GATEWAY_API_KEY not found in .env")
    return ""


def ensure_source(gateway: str, slug: str, display_name: str, api_key: str) -> None:
    """slug の source が gateway に未登録なら登録する。"""
    code, sources = gateway_request(gateway, "/api/v1/sources")
    if code != 200:
        raise SystemExit(f"failed sources: {code}")
    if not any(s.get("slug") == slug for s in sources):
        gateway_request(
            gateway,
            "/api/v1/sources/register",
            method="POST",
            payload={"slug": slug, "display_name": display_name},
            api_key=api_key,
        )


# ── state ─────────────────────────────────────────────────────────────────────

def load_state(path: Path) -> dict:
    if not path.exists():
        return {"known_external_ids": [], "last_run_at": None}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"known_external_ids": [], "last_run_at": None}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── テキスト処理 ──────────────────────────────────────────────────────────────

def strip_tags(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def iso_date_jp(s: str | None) -> str | None:
    """「2026/3/10」形式を含むテキストを JST 0時の ISO 8601 に変換する。"""
    if not s:
        return None
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}T00:00:00+09:00"


def now_utc_iso() -> str:
    """payload の collected_at 用タイムスタンプ。"""
    return datetime.now(UTC).isoformat()
