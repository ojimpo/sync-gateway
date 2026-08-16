#!/usr/bin/env python3
import argparse
import json
import random
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

from filmarks_common import extract_movie_jsonld, max_page, parse_cards
from sync_common import (
    ensure_source,
    gateway_request,
    load_api_key,
    load_state,
    save_state,
)


# マークが1件でもあるユーザーのページなら、1ページ目は必ず何か parse できる。
# 全ページ 0 件はスクレイプ破損（Filmarks の HTML 変更・遮断・ログイン要求）の
# サインであって「新着なし」ではない。ただし一時的な失敗で騒がないよう、
# 連続でこの回数に達してから異常として報告する（30分間隔なので3回=1.5時間）。
ZERO_PARSE_ALERT_AFTER = 3


def next_zero_parse_streak(previous: int | None, total_parsed: int) -> int:
    """パース0件の連続回数を更新する。1件でも取れたらリセット。"""
    return (int(previous or 0) + 1) if total_parsed == 0 else 0


def report_broken_scrape(gateway: str, api_key: str, streak: int, pages: int) -> None:
    """パース0件が続いていることを gateway に failed run として残す。

    cron のログは誰も見ないので（実際この破損は5ヶ月間見過ごされた）、
    他のソースと同じ runs テーブルに出して初めて気付ける状態にする。
    """
    message = (
        f"パース0件が{streak}回連続（{pages}ページ走査、HTTP取得は成功）。"
        "Filmarks側のHTML変更の可能性が高い。filmarks_common.parse_cards を確認すること。"
    )
    print(f"ALERT: {message}")
    # gateway_request は 4xx/5xx で HTTPError を投げるので、通信・認証エラーは
    # 例外側で拾う。通報に失敗しても同期本体は落とさない。
    try:
        _, sources = gateway_request(gateway, "/api/v1/sources")
        source_id = next((s["id"] for s in sources if s.get("slug") == "filmarks"), None)
        if source_id is None:
            print("ALERT: gateway に filmarks source が見つからず run を登録できない")
            return
        _, run = gateway_request(
            gateway, "/api/v1/runs", method="POST",
            payload={"source_id": source_id}, api_key=api_key,
        )
        gateway_request(
            gateway, f"/api/v1/runs/{run['id']}", method="PATCH",
            payload={"status": "failed", "error_message": message}, api_key=api_key,
        )
        print(f"ALERT: gateway に failed run を登録した (run_id={run['id']})")
    except Exception as e:
        print(f"ALERT: gateway への通報に失敗: {e}")


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
    total_parsed = 0
    pages_scanned = 0

    for p in range(1, pmax + 1):
        url = first_url if p == 1 else f"{first_url}?page={p}"
        r = sess.get(url, timeout=30)
        r.raise_for_status()
        recs = parse_cards(r.text, args.base_url)
        total_parsed += len(recs)
        pages_scanned = p
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

    # 「新着なし」と「パースが壊れて全部落としている」は new_records=0 では
    # 区別がつかない。走査したページの合計 parsed で切り分ける。
    zero_streak = next_zero_parse_streak(state.get("consecutive_zero_parse"), total_parsed)
    state["consecutive_zero_parse"] = zero_streak
    scrape_broken = zero_streak >= ZERO_PARSE_ALERT_AFTER
    if total_parsed == 0:
        print(f"WARN: parsed=0 (連続{zero_streak}回目)")

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
        if scrape_broken:
            report_broken_scrape(args.gateway, key, zero_streak, pages_scanned)
            raise SystemExit(1)
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
