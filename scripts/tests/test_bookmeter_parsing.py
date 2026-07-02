"""bookmeter 系スクリプトのパース処理の characterization test。"""
import bookmeter_sync_states_slow as bm


def test_iso_date():
    assert bm.iso_date("2026/03/10") == "2026-03-10T00:00:00+09:00"
    assert bm.iso_date("2026/3/1に読了") == "2026-03-01T00:00:00+09:00"
    assert bm.iso_date("不明") is None
    assert bm.iso_date(None) is None


def test_max_page_bookmeter_pattern():
    html = (
        '<a href="/users/1006219/books/read?page=2">2</a>'
        '<a href="/users/1006219/books/read?page=7">7</a>'
        '<a href="/users/1006219/books/wish?page=9">wish</a>'
    )
    assert bm.max_page(html, "1006219", "read") == 7
    assert bm.max_page(html, "1006219", "wish") == 9
    assert bm.max_page("<html></html>", "1006219", "read") == 1


def _book_li(inner: str) -> str:
    return f'<li class="group__book">{inner}</li>'


FULL_BOOK = _book_li(
    '<div class="detail__date">2026/03/10</div>'
    '<div class="detail__title"><a href="/books/111">テスト駆動開発</a></div>'
    '<ul class="detail__authors"><li><a href="/authors/1">Kent Beck</a></li></ul>'
    '<div class="detail__page">288</div>'
    '<a class="icon__review" href="/reviews/222">rev</a>'
)


def test_parse_page_full_book():
    items = bm.parse_page(FULL_BOOK, "https://bookmeter.com", "read")
    assert len(items) == 1
    r = items[0]
    assert r["source_slug"] == "bookmeter"
    assert r["external_id"] == "bmr_222"  # レビューがあれば bmr_<review_id>
    assert r["title"] == "テスト駆動開発"
    assert r["author"] == "Kent Beck"
    assert r["status"] == "read"
    assert r["rating"] is None
    assert r["event_date"] == "2026-03-10T00:00:00+09:00"
    p = r["payload"]
    assert p["book_id"] == "111"
    assert p["pages"] == 288
    assert p["review_url"] == "https://bookmeter.com/reviews/222"
    assert p["source_url"] == "https://bookmeter.com/books/111"


def test_parse_page_without_review_uses_composite_id():
    html = _book_li(
        '<div class="detail__date">2026/03/10</div>'
        '<div class="detail__title"><a href="/books/111">本</a></div>'
    )
    r = bm.parse_page(html, "https://bookmeter.com", "wish")[0]
    assert r["external_id"] == "bm_111_2026-03-10T00:00:00+09:00_wish"


def test_parse_page_without_date_uses_unknown():
    html = _book_li('<div class="detail__title"><a href="/books/111">本</a></div>')
    r = bm.parse_page(html, "https://bookmeter.com", "stacked")[0]
    assert r["external_id"] == "bm_111_unknown_stacked"
    assert r["event_date"] is None


def test_parse_page_skips_chunk_without_book_id():
    assert bm.parse_page(_book_li("<p>リンクなし</p>"), "https://bookmeter.com", "read") == []
