#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from sync_common import ensure_source, gateway_request, load_api_key, strip_tags


def parse_cards(html_text: str, base_url: str):
    records = []
    chunks = html_text.split('<div class="c-content-card">')[1:]
    for c in chunks:
        # movie id
        m = re.search(r'href="/movies/(\d+)(?:\?mark_id=(\d+))?"', c)
        if not m:
            continue
        movie_id = m.group(1)
        mark_id = m.group(2)

        # title + year text
        title = None
        year = None
        my = re.search(r'<h3 class="c-content-card__title">\s*<a [^>]*>(.*?)<span>\((\d{4})年製作の映画\)</span>', c, flags=re.S)
        if my:
            title = strip_tags(my.group(1))
            year = int(my.group(2))
        else:
            mt = re.search(r'<h3 class="c-content-card__title">\s*<a [^>]*>(.*?)</a>', c, flags=re.S)
            if mt:
                title = strip_tags(mt.group(1))

        # rating
        rating = None
        mr = re.search(r'<div class="c-rating__score">([0-9.\-]+)</div>', c)
        if mr:
            txt = mr.group(1).strip()
            if txt != "-":
                try:
                    rating = float(txt)
                except ValueError:
                    rating = None

        # review teaser text
        review = None
        mrev = re.search(r'<p class="c-content-card__review">(.*?)</p>', c, flags=re.S)
        if mrev:
            review = strip_tags(mrev.group(1).replace('>>続きを読む', ''))

        # review id/url
        review_id = None
        mri = re.search(r'/reviews/(\d+)', c)
        if mri:
            review_id = mri.group(1)

        source_url = f"{base_url}/movies/{movie_id}"
        if review_id:
            source_url = f"{base_url}/movies/{movie_id}/reviews/{review_id}"

        # external_id: mark_id > review_id > movie_id hash fallback
        if mark_id:
            external_id = f"fm_mark_{mark_id}"
        elif review_id:
            external_id = f"fm_review_{review_id}"
        elif movie_id:
            external_id = f"fm_movie_{movie_id}"
        else:
            external_id = "fm_" + hashlib.sha1(source_url.encode()).hexdigest()[:16]

        records.append(
            {
                "source_slug": "filmarks",
                "external_id": external_id,
                "record_type": "movie",
                "title": title,
                "author": None,
                "rating": rating,
                "status": "watched",
                "event_date": None,
                "payload": {
                    "source_url": source_url,
                    "movie_id": movie_id,
                    "mark_id": mark_id,
                    "review_id": review_id,
                    "review": review,
                    "year": year,
                    "collected_at": datetime.utcnow().isoformat() + "Z",
                },
            }
        )
    return records


def max_page(html_text: str, user_slug: str) -> int:
    nums = [int(x) for x in re.findall(rf'/users/{re.escape(user_slug)}\?page=(\d+)', html_text)]
    return max(nums) if nums else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-slug", default="ojimpo")
    ap.add_argument("--gateway", default="http://localhost:18000")
    ap.add_argument("--base-url", default="https://filmarks.com")
    ap.add_argument("--max-pages", type=int, default=2)
    ap.add_argument("--delay-min", type=float, default=2.5)
    ap.add_argument("--delay-max", type=float, default=6.0)
    ap.add_argument("--chunk-size", type=int, default=100)
    ap.add_argument("--limit", type=int, default=20, help="max records to ingest after dedupe")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    key = load_api_key(repo)

    if not args.dry_run:
        ensure_source(args.gateway, "filmarks", "Filmarks", key)

    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})

    first_url = f"{args.base_url}/users/{args.user_slug}"
    r0 = sess.get(first_url, timeout=30)
    r0.raise_for_status()
    pmax = min(max_page(r0.text, args.user_slug), args.max_pages)
    print(f"user={args.user_slug} pages={pmax}")

    all_records = []
    for p in range(1, pmax + 1):
        url = first_url if p == 1 else f"{first_url}?page={p}"
        r = sess.get(url, timeout=30)
        r.raise_for_status()
        recs = parse_cards(r.text, args.base_url)
        print(f"  page={p} records={len(recs)}")
        all_records.extend(recs)
        if p < pmax:
            time.sleep(random.uniform(args.delay_min, args.delay_max))

    dedup = {}
    for r in all_records:
        dedup.setdefault(r["external_id"], r)
    records = list(dedup.values())
    print(f"total={len(all_records)} deduped={len(records)}")

    if args.limit and args.limit > 0:
        records = records[: args.limit]
        print(f"limited={len(records)}")

    if args.dry_run:
        print(json.dumps(records[:5], ensure_ascii=False, indent=2))
        return

    ok = fail = 0
    for i in range(0, len(records), args.chunk_size):
        batch = records[i : i + args.chunk_size]
        code, resp = gateway_request(
            args.gateway,
            "/api/v1/ingest/events",
            method="POST",
            payload={"records": batch},
            api_key=key,
        )
        print(
            f"ingest chunk {i//args.chunk_size+1}: code={code} accepted={resp.get('accepted')} failed={resp.get('failed')}"
        )
        ok += int(resp.get("accepted", 0))
        fail += int(resp.get("failed", 0))
        time.sleep(random.uniform(args.delay_min, args.delay_max))
    print(f"done accepted={ok} failed={fail}")


if __name__ == "__main__":
    main()
