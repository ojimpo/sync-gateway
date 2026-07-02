#!/usr/bin/env python3
import argparse
import hashlib
import json
import random
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from sync_common import (
    ensure_source,
    gateway_request,
    load_api_key,
    load_state,
    save_state,
    strip_tags,
)


def parse_cards(html_text: str, base_url: str):
    records = []
    chunks = html_text.split('<div class="c-content-card">')[1:]
    for c in chunks:
        m = re.search(r'href="/movies/(\d+)(?:\?mark_id=(\d+))?"', c)
        if not m:
            continue
        movie_id = m.group(1)
        mark_id = m.group(2)

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

        rating = None
        mr = re.search(r'<div class="c-rating__score">([0-9.\-]+)</div>', c)
        if mr:
            txt = mr.group(1).strip()
            if txt != "-":
                try:
                    rating = float(txt)
                except ValueError:
                    rating = None

        review = None
        mrev = re.search(r'<p class="c-content-card__review">(.*?)</p>', c, flags=re.S)
        if mrev:
            review = strip_tags(mrev.group(1).replace('>>続きを読む', ''))

        review_id = None
        mri = re.search(r'/reviews/(\d+)', c)
        if mri:
            review_id = mri.group(1)

        source_url = f"{base_url}/movies/{movie_id}"
        if review_id:
            source_url = f"{base_url}/movies/{movie_id}/reviews/{review_id}"

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
                    "collected_at": datetime.now(UTC).isoformat(),
                },
            }
        )
    return records


def extract_movie_jsonld(html_text: str) -> dict | None:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html_text, flags=re.S)
    for raw in blocks:
        s = raw.strip()
        try:
            obj = json.loads(s)
        except Exception:
            continue
        if isinstance(obj, dict) and obj.get("@type") == "Movie":
            return obj
    return None


def enrich_record_with_movie_detail(session: requests.Session, record: dict, delay_min: float, delay_max: float):
    movie_id = record.get("payload", {}).get("movie_id")
    if not movie_id:
        return

    detail_url = f"https://filmarks.com/movies/{movie_id}"
    r = session.get(detail_url, timeout=30)
    r.raise_for_status()

    meta = extract_movie_jsonld(r.text)
    if not meta:
        return

    directors = [p.get("name") for p in (meta.get("director") or []) if isinstance(p, dict) and p.get("name")]
    actors = [p.get("name") for p in (meta.get("actor") or []) if isinstance(p, dict) and p.get("name")]
    countries = [c.get("name") for c in (meta.get("countries") or []) if isinstance(c, dict) and c.get("name")]
    genres = meta.get("genres") or []

    # gateway共通のauthor欄には先頭監督を設定
    if directors:
        record["author"] = directors[0]

    # 公開日を event_date に採用（鑑賞日が取れないため）
    if not record.get("event_date"):
        rd = meta.get("releaseDate")
        if isinstance(rd, str) and rd:
            record["event_date"] = rd

    payload = record.setdefault("payload", {})
    payload["source_url"] = payload.get("source_url") or detail_url
    payload["detail_url"] = detail_url
    payload["directors"] = directors
    payload["cast"] = actors
    payload["countries"] = countries
    payload["genres"] = genres
    payload["runtime_iso8601"] = meta.get("playTime")

    # 詳細ページ連打を避ける
    time.sleep(random.uniform(delay_min, delay_max))


def max_page(html_text: str, user_slug: str) -> int:
    nums = [int(x) for x in re.findall(rf'/users/{re.escape(user_slug)}\?page=(\d+)', html_text)]
    return max(nums) if nums else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user-slug", default="ojimpo")
    ap.add_argument("--gateway", default="http://localhost:18000")
    ap.add_argument("--base-url", default="https://filmarks.com")
    ap.add_argument("--max-pages", type=int, default=3)
    ap.add_argument("--delay-min", type=float, default=2.0)
    ap.add_argument("--delay-max", type=float, default=5.0)
    ap.add_argument("--chunk-size", type=int, default=100)
    ap.add_argument("--state-file", default=None)
    ap.add_argument("--state-keep", type=int, default=5000)
    ap.add_argument("--bootstrap-from-gateway", action="store_true", default=True)
    ap.add_argument("--no-bootstrap-from-gateway", dest="bootstrap_from_gateway", action="store_false")
    ap.add_argument("--enrich-details", action="store_true", default=True)
    ap.add_argument("--no-enrich-details", dest="enrich_details", action="store_false")
    ap.add_argument("--detail-delay-min", type=float, default=1.0)
    ap.add_argument("--detail-delay-max", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[1]
    key = load_api_key(repo)
    state_path = Path(args.state_file) if args.state_file else (repo / "scripts" / "state" / "filmarks_delta_state.json")

    if not args.dry_run:
        ensure_source(args.gateway, "filmarks", "Filmarks", key)

    state = load_state(state_path)
    known_ids = list(state.get("known_external_ids") or [])

    # 初回のみ gateway 既存データで known を埋める
    if not known_ids and args.bootstrap_from_gateway:
        code, rows = gateway_request(args.gateway, "/api/v1/records?source=filmarks&limit=500")
        if code == 200 and isinstance(rows, list):
            known_ids = [r.get("external_id") for r in rows if r.get("external_id")]
            print(f"bootstrapped known ids from gateway: {len(known_ids)}")

    known_set = set(known_ids)

    sess = requests.Session()
    sess.headers.update({"User-Agent": "Mozilla/5.0"})

    first_url = f"{args.base_url}/users/{args.user_slug}"
    r0 = sess.get(first_url, timeout=30)
    r0.raise_for_status()
    pmax = min(max_page(r0.text, args.user_slug), args.max_pages)
    print(f"user={args.user_slug} scan_pages={pmax}")

    new_records = []
    seen_new = set()
    hit_known = False

    for p in range(1, pmax + 1):
        url = first_url if p == 1 else f"{first_url}?page={p}"
        r = sess.get(url, timeout=30)
        r.raise_for_status()
        recs = parse_cards(r.text, args.base_url)
        print(f"  page={p} parsed={len(recs)}")

        for rec in recs:
            eid = rec["external_id"]
            if eid in known_set:
                hit_known = True
                break
            if eid not in seen_new:
                seen_new.add(eid)
                new_records.append(rec)

        if hit_known:
            print(f"  stop at page={p} (known id reached)")
            break

        if p < pmax:
            time.sleep(random.uniform(args.delay_min, args.delay_max))

    print(f"new_records={len(new_records)}")

    if new_records and args.enrich_details:
        print(f"enriching details for {len(new_records)} records...")
        for rec in new_records:
            try:
                enrich_record_with_movie_detail(sess, rec, args.detail_delay_min, args.detail_delay_max)
            except Exception as e:
                rec.setdefault("payload", {})["detail_enrich_error"] = str(e)

    if args.dry_run:
        print(json.dumps(new_records[:5], ensure_ascii=False, indent=2))
        return

    if not new_records:
        state["last_run_at"] = datetime.now(UTC).isoformat()
        state["last_new_count"] = 0
        save_state(state_path, state)
        print("done no change")
        return

    ok = fail = 0
    for i in range(0, len(new_records), args.chunk_size):
        batch = new_records[i : i + args.chunk_size]
        code, resp = gateway_request(
            args.gateway,
            "/api/v1/ingest/events",
            method="POST",
            payload={"records": batch},
            api_key=key,
        )
        print(f"ingest chunk {i//args.chunk_size+1}: code={code} accepted={resp.get('accepted')} failed={resp.get('failed')}")
        ok += int(resp.get("accepted", 0))
        fail += int(resp.get("failed", 0))
        time.sleep(random.uniform(args.delay_min, args.delay_max))

    merged = [r["external_id"] for r in new_records] + known_ids
    dedup_merged = []
    seen = set()
    for eid in merged:
        if eid and eid not in seen:
            seen.add(eid)
            dedup_merged.append(eid)
    state["known_external_ids"] = dedup_merged[: args.state_keep]
    state["last_run_at"] = datetime.now(UTC).isoformat()
    state["last_new_count"] = len(new_records)
    state["last_ingest_accepted"] = ok
    state["last_ingest_failed"] = fail
    save_state(state_path, state)

    print(f"done accepted={ok} failed={fail}")


if __name__ == "__main__":
    main()
