#!/usr/bin/env python3
import argparse
import json
import random
import time
from pathlib import Path

import requests

from filmarks_common import max_page, parse_cards
from sync_common import ensure_source, gateway_request, load_api_key


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
