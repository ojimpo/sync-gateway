#!/usr/bin/env python3
"""Studyplus daily study-time sync → sync-gateway ingest.

Auth flow:
  1. POST /2/client_auth with consumer_key/secret + email/password → access_token
  2. GET /2/timeline_feeds/followee?access_token=... → study records (with duration)
  3. Aggregate by date → ingest one record per day

Usage:
  python3 studyplus_sync.py                    # incremental sync
  python3 studyplus_sync.py --full-backfill    # paginate through all history
  python3 studyplus_sync.py --dry-run          # preview without ingesting
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

import requests

# ── Constants ──────────────────────────────────────────────────────────────────

STUDYPLUS_API = "https://api.studyplus.jp/2"


def _load_env_value(name: str) -> str:
    """Read a value from the environment, falling back to the repo .env file."""
    val = os.environ.get(name, "")
    if val:
        return val
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return ""


CONSUMER_KEY = _load_env_value("STUDYPLUS_CONSUMER_KEY")
CONSUMER_SECRET = _load_env_value("STUDYPLUS_CONSUMER_SECRET")

# 1Password vault item for credentials
OP_VAULT = "OpenClaw"
OP_ITEM = "Studyplus"

# ── Credential helpers ────────────────────────────────────────────────────────

def get_credentials_from_1password() -> tuple[str, str]:
    """Retrieve Studyplus email/password from 1Password service account."""
    env_file = Path.home() / ".config" / "op" / "service-account.env"
    if not env_file.exists():
        raise RuntimeError("1Password service-account.env not found")

    # Source the env file (need bash for 'source')
    cmd = (
        f"set -a; source {env_file}; set +a; "
        f"op item get --vault '{OP_VAULT}' '{OP_ITEM}' --fields username,password --format json"
    )
    result = subprocess.run(cmd, shell=True, executable="/bin/bash", capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"1Password lookup failed: {result.stderr.strip()}")

    fields = json.loads(result.stdout)
    creds = {f["label"]: f["value"] for f in fields}
    email = creds.get("username") or creds.get("email", "")
    password = creds.get("password", "")
    if not email or not password:
        raise RuntimeError(f"Incomplete credentials from 1Password: keys={list(creds)}")
    return email, password


def get_credentials_from_env() -> tuple[str, str]:
    """Fallback: read from env vars."""
    email = os.environ.get("STUDYPLUS_EMAIL", "")
    password = os.environ.get("STUDYPLUS_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("STUDYPLUS_EMAIL / STUDYPLUS_PASSWORD not set")
    return email, password


def get_credentials() -> tuple[str, str]:
    try:
        return get_credentials_from_1password()
    except Exception as e:
        print(f"[warn] 1Password lookup failed ({e}), trying env vars", file=sys.stderr)
        return get_credentials_from_env()

# ── Studyplus API ─────────────────────────────────────────────────────────────

def authenticate(email: str, password: str) -> dict:
    """Authenticate with Studyplus API → returns {access_token, refresh_token, username}."""
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise RuntimeError("STUDYPLUS_CONSUMER_KEY / STUDYPLUS_CONSUMER_SECRET not set (env or repo .env)")
    resp = requests.post(
        f"{STUDYPLUS_API}/client_auth",
        json={
            "consumer_key": CONSUMER_KEY,
            "consumer_secret": CONSUMER_SECRET,
            "username": email,
            "password": password,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_access_token(refresh_token: str) -> dict:
    """Refresh an expired access_token."""
    resp = requests.post(
        f"{STUDYPLUS_API}/client_auth",
        json={
            "consumer_key": CONSUMER_KEY,
            "consumer_secret": CONSUMER_SECRET,
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_timeline_page(access_token: str, cursor: str | None = None) -> dict:
    """Fetch one page of followee timeline (includes own records).

    Returns: {"current": ..., "next": ..., "feeds": [...]}
    """
    params = {"access_token": access_token}
    if cursor:
        params["next"] = cursor
    resp = requests.get(
        f"{STUDYPLUS_API}/timeline_feeds/followee",
        params=params,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_records_existing(access_token: str, date_from: str, date_to: str) -> dict:
    """Check which dates have study records in a given range.

    Returns: {"exists": [{"date": "YYYY-MM-DD", "existing": bool}, ...]}
    """
    resp = requests.get(
        f"{STUDYPLUS_API}/me/records/existing",
        params={"access_token": access_token, "from": date_from, "to": date_to},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def collect_all_records(access_token: str, max_pages: int = 100) -> list[dict]:
    """Paginate through timeline to collect all study_record feeds."""
    all_feeds = []
    seen_event_ids = set()
    cursor = None
    seen_cursors = set()
    no_new_count = 0

    for page in range(max_pages):
        data = fetch_timeline_page(access_token, cursor)
        feeds = data.get("feeds", [])
        next_cursor = data.get("next")

        new_count = 0
        for f in feeds:
            if f.get("feed_type") != "study_record":
                continue
            eid = f.get("body_study_record", {}).get("event_id") or f.get("body_study_record", {}).get("record_id")
            if eid and eid not in seen_event_ids:
                seen_event_ids.add(eid)
                all_feeds.append(f)
                new_count += 1

        print(f"  page {page + 1}: {new_count} new study records (total: {len(all_feeds)})")

        # Stop if: no next cursor, cursor repeats, or no new records for 2 consecutive pages
        if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            break
        if new_count == 0:
            no_new_count += 1
            if no_new_count >= 2:
                print("  stopping: no new records for 2 consecutive pages")
                break
        else:
            no_new_count = 0

        seen_cursors.add(next_cursor)
        cursor = next_cursor
        time.sleep(0.5)  # gentle rate limiting

    return all_feeds


def aggregate_daily(records: list[dict]) -> dict[str, dict]:
    """Aggregate raw study records into per-day summaries.

    Returns: {"YYYY-MM-DD": {"minutes": int, "title": str, "sessions": int}}
    """
    daily = {}
    for feed in records:
        body = feed.get("body_study_record", {})
        date = body.get("record_date")
        if not date:
            continue
        duration_sec = body.get("duration", 0)
        minutes = round(duration_sec / 60)
        title = body.get("material_title") or ""

        if date not in daily:
            daily[date] = {"minutes": 0, "title": title, "sessions": 0}
        daily[date]["minutes"] += minutes
        # Keep the first title (or longest one)
        if len(title) > len(daily[date]["title"]):
            daily[date]["title"] = title
        daily[date]["sessions"] += 1

    return daily


# ── Gateway helpers ───────────────────────────────────────────────────────────

def load_api_key(repo_root: Path) -> str:
    env = repo_root / ".env"
    if not env.exists():
        raise RuntimeError(".env not found")
    for line in env.read_text().splitlines():
        if line.startswith("GATEWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GATEWAY_API_KEY not found in .env")


def gateway_request(base: str, path: str, method: str = "GET", payload=None, api_key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode() or "{}"
        return res.status, json.loads(body)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"known_external_ids": [], "last_run_at": None}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"known_external_ids": [], "last_run_at": None}


def save_state(path: Path, state: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def build_ingest_records(daily: dict[str, dict]) -> list[dict]:
    """Convert daily summaries to ingest-ready records."""
    records = []
    for date, info in sorted(daily.items()):
        records.append({
            "source_slug": "studyplus",
            "external_id": f"studyplus_{date}",
            "record_type": "study",
            "title": info["title"],
            "event_date": f"{date}T00:00:00+09:00",
            "payload": {"minutes": info["minutes"]},
        })
    return records


def main():
    ap = argparse.ArgumentParser(description="Sync Studyplus study time → sync-gateway")
    ap.add_argument("--gateway", default="http://localhost:18000")
    ap.add_argument("--full-backfill", action="store_true", help="Paginate through all history")
    ap.add_argument("--max-pages", type=int, default=100, help="Max timeline pages for backfill")
    ap.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    ap.add_argument("--state-file", default=None)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    key = load_api_key(repo)
    state_path = Path(args.state_file) if args.state_file else (repo / "scripts" / "state" / "studyplus_state.json")

    # ── Auth ──
    email, password = get_credentials()
    auth = authenticate(email, password)
    access_token = auth["access_token"]
    print(f"[auth] OK  username={auth['username']}")

    # ── Collect records ──
    if args.full_backfill:
        print("[collect] Full backfill mode")
        records = collect_all_records(access_token, max_pages=args.max_pages)
    else:
        # Incremental: just grab the latest page
        print("[collect] Incremental mode (1 page)")
        data = fetch_timeline_page(access_token)
        records = [f for f in data.get("feeds", []) if f.get("feed_type") == "study_record"]
        print(f"  page 1: {len(records)} study records")

    if not records:
        print("[done] No study records found")
        return

    # ── Aggregate ──
    daily = aggregate_daily(records)
    print(f"[aggregate] {len(daily)} unique days")
    for date, info in sorted(daily.items()):
        print(f"  {date}: {info['minutes']}min ({info['sessions']} session(s)) {info['title']}")

    # ── Build ingest records ──
    ingest_records = build_ingest_records(daily)

    # ── Dedup via state ──
    state = load_state(state_path)
    known_ids = set(state.get("known_external_ids", []))
    new_records = [r for r in ingest_records if r["external_id"] not in known_ids]
    skipped = len(ingest_records) - len(new_records)
    if skipped:
        print(f"[dedup] {skipped} already ingested, {len(new_records)} new")

    if not new_records:
        state["last_run_at"] = datetime.now(UTC).isoformat()
        state["last_new_count"] = 0
        save_state(state_path, state)
        print("[done] No new records to ingest")
        return

    # ── Dry run ──
    if args.dry_run:
        print("[dry-run] Would ingest:")
        print(json.dumps(new_records, ensure_ascii=False, indent=2))
        return

    # ── Ingest ──
    code, resp = gateway_request(
        args.gateway,
        "/api/v1/ingest/events",
        method="POST",
        payload={"records": new_records},
        api_key=key,
    )
    accepted = resp.get("accepted", 0)
    failed = resp.get("failed", 0)
    print(f"[ingest] HTTP {code}: accepted={accepted} failed={failed}")

    if failed:
        print(f"[warn] Failed records: {resp.get('errors', [])}")

    # ── Update state ──
    all_ids = [r["external_id"] for r in new_records] + list(known_ids)
    state["known_external_ids"] = list(dict.fromkeys(all_ids))[:5000]
    state["last_run_at"] = datetime.now(UTC).isoformat()
    state["last_new_count"] = len(new_records)
    state["last_ingest_accepted"] = accepted
    state["last_ingest_failed"] = failed
    save_state(state_path, state)

    print(f"[done] accepted={accepted} failed={failed}")


if __name__ == "__main__":
    main()
