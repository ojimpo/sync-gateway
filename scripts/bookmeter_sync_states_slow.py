#!/usr/bin/env python3
import argparse
import html
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

import requests

STATE_PATH = {
    "read": "read",
    "reading": "reading",
    "wish": "wish",
    "stacked": "stacked",
}


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


def parse_page(html_text: str, base_url: str, status_value: str):
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

        review_id = None
        review_url = None
        m = re.search(r'class="icon__review" href="/reviews/(\d+)"', c)
        if m:
            review_id = m.group(1)
            review_url = f"{base_url}/reviews/{review_id}"

        source_url = f"{base_url}/books/{book_id}"
        if review_id:
            external_id = f"bmr_{review_id}"
        else:
            external_id = f"bm_{book_id}_{iso_date(date_txt) or 'unknown'}_{status_value}"

        items.append(
            {
                "source_slug": "bookmeter",
                "external_id": external_id,
                "record_type": "book",
                "title": title,
                "author": author,
                "rating": None,
                "status": status_value,
                "event_date": iso_date(date_txt),
                "payload": {
                    "source_url": source_url,
                    "book_id": book_id,
                    "review_id": review_id,
                    "review_url": review_url,
                    "pages": pages,
                    "raw_date_text": date_txt,
                    "collected_at": datetime.utcnow().isoformat() + "Z",
                },
            }
        )
    return items


def max_page(html_text: str, user_id: str, path_key: str) -> int:
    nums = [int(x) for x in re.findall(rf'/users/{user_id}/books/{path_key}\?page=(\d+)', html_text)]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-id", default="1006219")
    ap.add_argument("--gateway", default="http://localhost:18000")
    ap.add_argument("--base-url", default="https://bookmeter.com")
    ap.add_argument("--states", default="read,reading,wish,stacked")
    ap.add_argument("--max-pages", type=int, default=3, help="pages per state; for first full import set large value")
    ap.add_argument("--delay-min", type=float, default=3.0)
    ap.add_argument("--delay-max", type=float, default=7.0)
    ap.add_argument("--chunk-size", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    key = load_api_key(repo)

    code, sources = gateway_request(args.gateway, "/api/v1/sources")
    if code != 200:
        raise SystemExit(f"failed sources: {code}")
    if not any(s.get("slug") == "bookmeter" for s in sources) and not args.dry_run:
        gateway_request(args.gateway, "/api/v1/sources/register", method="POST", payload={"slug": "bookmeter", "display_name": "読書メーター"}, api_key=key)

    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})

    all_records = []
    for st in [s.strip() for s in args.states.split(",") if s.strip()]:
        if st not in STATE_PATH:
            print(f"skip unknown state: {st}")
            continue
        path_key = STATE_PATH[st]
        first_url = f"{args.base_url}/users/{args.user_id}/books/{path_key}"
        r0 = sess.get(first_url, timeout=30)
        r0.raise_for_status()
        pmax = min(max_page(r0.text, args.user_id, path_key), args.max_pages)
        print(f"state={st} pages={pmax}")

        for p in range(1, pmax + 1):
            url = first_url if p == 1 else f"{first_url}?page={p}"
            r = sess.get(url, timeout=30)
            r.raise_for_status()
            recs = parse_page(r.text, args.base_url, st)
            print(f"  page={p} records={len(recs)}")
            all_records.extend(recs)
            if p < pmax:
                time.sleep(random.uniform(args.delay_min, args.delay_max))

    dedup = {}
    for r in all_records:
        dedup.setdefault(r["external_id"], r)
    records = list(dedup.values())
    print(f"total={len(all_records)} deduped={len(records)}")

    if args.dry_run:
        print(json.dumps(records[:3], ensure_ascii=False, indent=2))
        return

    ok = fail = 0
    for i in range(0, len(records), args.chunk_size):
        batch = records[i : i + args.chunk_size]
        code, resp = gateway_request(args.gateway, "/api/v1/ingest/events", method="POST", payload={"records": batch}, api_key=key)
        print(f"ingest chunk {i//args.chunk_size+1}: code={code} accepted={resp.get('accepted')} failed={resp.get('failed')}")
        ok += int(resp.get("accepted", 0))
        fail += int(resp.get("failed", 0))
        time.sleep(random.uniform(args.delay_min, args.delay_max))
    print(f"done accepted={ok} failed={fail}")


if __name__ == "__main__":
    main()
