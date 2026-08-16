"""Filmarks ユーザーページの HTML パース処理（delta / slow スクリプト共用）。"""
import hashlib
import json
import re

from sync_common import now_utc_iso, strip_tags

# カード先頭の作品リンクから movie_id と mark_id を取る。
# mark_id の付き方は Filmarks 側で変わっており、両方を受ける:
#   旧 (〜2026-03-25): /movies/118757?mark_id=216980657
#   新 (2026-03-25〜): /movies/118757#mark-216980657
# 旧形式しか見ていなかったため、2026-03-25 05:00〜05:30 の切り替わりで
# 全カードが弾かれ、約5ヶ月間 parsed=0 のまま無音で止まっていた。
# mark_id なし (/movies/118757") も従来どおり許容する（external_id は
# review_id → movie_id にフォールバックする）。
MOVIE_LINK_RE = re.compile(r'href="/movies/(\d+)(?:(?:\?mark_id=|#mark-)(\d+))?"')


def parse_cards(html_text: str, base_url: str) -> list[dict]:
    records = []
    chunks = html_text.split('<div class="c-content-card">')[1:]
    for c in chunks:
        m = MOVIE_LINK_RE.search(c)
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

        # external_id: mark_id > review_id > movie_id > URLハッシュ の優先順
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
                    "collected_at": now_utc_iso(),
                },
            }
        )
    return records


def max_page(html_text: str, user_slug: str) -> int:
    nums = [int(x) for x in re.findall(rf'/users/{re.escape(user_slug)}\?page=(\d+)', html_text)]
    return max(nums) if nums else 1


# レビュー詳細ページの投稿日時。ユーザー一覧のカードには日付が一切無いので、
# 鑑賞日を知るにはここを見るしかない。Filmarks は日本のサービスなので JST 扱い。
REVIEW_DATE_RE = re.compile(
    r'<time[^>]*class="[^"]*c-media__date[^"]*"[^>]*datetime="(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})'
)


def extract_review_datetime(html_text: str) -> str | None:
    """レビュー詳細ページから投稿日時を ISO8601(+09:00) で返す。無ければ None。"""
    m = REVIEW_DATE_RE.search(html_text)
    if not m:
        return None
    return f"{m.group(1)}T{m.group(2)}:00+09:00"


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
