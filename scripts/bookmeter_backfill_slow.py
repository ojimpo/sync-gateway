#!/usr/bin/env python3
import argparse
import html
import json
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def iso_date(s: str | None) -> str | None:
    if not s:
        return None
    m = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", s)
    if not m:
        return None
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}T00:00:00+09:00"


def strip_tags(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def parse_read_page(html_text: str, base_url: str):
    items = []
    chunks = html_text.split('<li class="group__book">')[1:]

    for c in chunks:
        book_id = None
        m = re.search(r'<div class="detail__title">\s*<a href="/books/(\d+)"', c, flags=re.S)
        if m:
            book_id = m.group(1)
        if not book_id:
            m = re.search(r'href="/books/(\d+)"', c)
            if m:
                book_id = m.group(1)
        if not book_id:
            continue

        title = None
        m = re.search(r'<div class="detail__title">\s*<a [^>]*>(.*?)</a>', c, flags=re.S)
        if m:
            title = strip_tags(m.group(1))

        author = None
        m = re.search(r'<ul class="detail__authors">([\s\S]*?)</ul>', c)
        if m:
            ma = re.search(r'<a [^>]*>(.*?)</a>', m.group(1), flags=re.S)
            if ma:
                author = strip_tags(ma.group(1))

        date_txt = None
        m = re.search(r'<div class="detail__date">(.*?)</div>', c, flags=re.S)
        if m:
            date_txt = strip_tags(m.group(1))

        pages = None
        m = re.search(r'<div class="detail__page">(\d+)</div>', c)
        if m:
            pages = int(m.group(1))

        registered_count = None
        m = re.search(r'<dd class="options__item">(\d+)</dd>', c)
        if m:
            registered_count = int(m.group(1))

        cover_image_url = None
        m = re.search(r'<img [^>]*class="cover__image"[^>]*src="([^"]+)"', c)
        if m:
            cover_image_url = html.unescape(m.group(1))

        review_url = None
        review_id = None
        m = re.search(r'class="icon__review" href="/reviews/(\d+)"', c)
        if m:
            review_id = m.group(1)
            review_url = f"{base_url}/reviews/{review_id}"

        source_url = f"{base_url}/books/{book_id}"

        # event-first key: prefer review id, fallback to book+date
        if review_id:
            external_id = f"bmr_{review_id}"
        else:
            external_id = f"bm_{book_id}_{iso_date(date_txt) or 'unknown'}"

        rec = {
            "source_slug": "bookmeter",
            "external_id": external_id,
            "record_type": "book",
            "title": title,
            "author": author,
            "rating": None,
            "status": "read",
            "event_date": iso_date(date_txt),
            "payload": {
                "source_url": source_url,
                "book_id": book_id,
                "review_id": review_id,
                "review_url": review_url,
                "review_text": None,
                "review_likes": None,
                "registered_count": registered_count,
                "isbn": None,
                "publisher": None,
                "published_date": None,
                "pages": pages,
                "cover_image_url": cover_image_url,
                "raw_date_text": date_txt,
                "collected_at": datetime.utcnow().isoformat() + "Z",
            },
        }
        items.append(rec)
    return items


def get_max_page(html_text: str, user_id: str) -> int:
    nums = [int(x) for x in re.findall(rf'/users/{user_id}/books/read\?page=(\d+)', html_text)]
    return max(nums) if nums else 1


def gateway_request(base: str, path: str, method: str = "GET", payload=None, api_key: str | None = None):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    req = Request(base.rstrip("/") + path, data=data, headers=headers, method=method)
    with urlopen(req, timeout=30) as res:
        body = res.read().decode() or "{}"
        return res.status, json.loads(body)


def load_api_key(repo_root: Path) -> str:
    env = repo_root / ".env"
    if not env.exists():
        return ""
    for line in env.read_text().splitlines():
        if line.startswith("GATEWAY_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def fetch_with_retry(session: requests.Session, url: str, timeout: int = 30, retries: int = 6):
    last_err = None
    for i in range(retries):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(30, 2 + i * 3) + random.uniform(0.3, 1.8)
                print(f"warn: {r.status_code} for {url} (retry {i+1}/{retries}, wait {wait:.1f}s)")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            last_err = e
            wait = min(30, 2 + i * 3) + random.uniform(0.3, 1.8)
            print(f"warn: request error for {url} (retry {i+1}/{retries}, wait {wait:.1f}s): {e}")
            time.sleep(wait)
    raise RuntimeError(f"failed to fetch after retries: {url} :: {last_err}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", default="1006219")
    ap.add_argument("--base-url", default="https://bookmeter.com")
    ap.add_argument("--gateway", default="http://localhost:18000")
    ap.add_argument("--delay-min", type=float, default=2.0)
    ap.add_argument("--delay-max", type=float, default=4.0)
    ap.add_argument("--chunk-size", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    api_key = load_api_key(repo)

    session = requests.Session()
    retry = Retry(total=0, connect=0, read=0)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
    )

    # ensure source exists
    code, sources = gateway_request(args.gateway, "/api/v1/sources")
    if code != 200:
        raise SystemExit(f"failed sources: {code}")
    if not any(s.get("slug") == "bookmeter" for s in sources):
        if args.dry_run:
            print("[dry-run] would register source bookmeter")
        else:
            gateway_request(
                args.gateway,
                "/api/v1/sources/register",
                method="POST",
                payload={"slug": "bookmeter", "display_name": "読書メーター"},
                api_key=api_key,
            )

    url0 = f"{args.base_url}/users/{args.user_id}/books/read"
    r0 = fetch_with_retry(session, url0, timeout=30)
    max_page = get_max_page(r0.text, args.user_id)
    print(f"max_page={max_page}")

    all_records = []
    for p in range(1, max_page + 1):
        url = url0 if p == 1 else f"{url0}?page={p}"
        r = fetch_with_retry(session, url, timeout=30)
        page_records = parse_read_page(r.text, args.base_url)
        print(f"page={p} records={len(page_records)}")
        all_records.extend(page_records)
        if p < max_page:
            time.sleep(random.uniform(args.delay_min, args.delay_max))

    # dedupe by external_id keep first occurrence (latest pages are first)
    dedup = {}
    for rec in all_records:
        dedup.setdefault(rec["external_id"], rec)
    records = list(dedup.values())
    print(f"total_records={len(all_records)} deduped={len(records)}")

    if args.dry_run:
        print(json.dumps(records[:3], ensure_ascii=False, indent=2))
        return

    ok = 0
    fail = 0
    for i in range(0, len(records), args.chunk_size):
        batch = records[i : i + args.chunk_size]
        code, resp = gateway_request(
            args.gateway,
            "/api/v1/ingest/events",
            method="POST",
            payload={"records": batch},
            api_key=api_key,
        )
        print(f"ingest chunk {i//args.chunk_size+1}: code={code} accepted={resp.get('accepted')} failed={resp.get('failed')}")
        ok += int(resp.get("accepted", 0))
        fail += int(resp.get("failed", 0))
        time.sleep(random.uniform(args.delay_min, args.delay_max))

    print(f"done accepted={ok} failed={fail}")


if __name__ == "__main__":
    main()
