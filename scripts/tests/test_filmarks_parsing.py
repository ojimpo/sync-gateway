"""filmarks 系スクリプトの HTML パース処理の characterization test。

filmarks_sync_delta / filmarks_sync_slow に重複実装されている関数が
同じ挙動であることも（共通化の前提として）ここで固定する。
"""
import pytest

import filmarks_sync_delta as delta
import filmarks_sync_slow as slow

MODULES = [delta, slow]


def card(inner: str) -> str:
    return f'<div class="c-content-card">{inner}</div>'

FULL_CARD = card(
    '<h3 class="c-content-card__title">'
    '<a href="/movies/123?mark_id=456">インターステラー<span>(2014年製作の映画)</span></a></h3>'
    '<div class="c-rating__score">4.5</div>'
    '<p class="c-content-card__review">とても良かった&amp;泣いた>>続きを読む</p>'
    '<a href="/movies/123/reviews/789">review</a>'
)


@pytest.mark.parametrize("mod", MODULES)
class TestParseCards:
    def test_full_card(self, mod):
        recs = mod.parse_cards(FULL_CARD, "https://filmarks.com")
        assert len(recs) == 1
        r = recs[0]
        assert r["source_slug"] == "filmarks"
        assert r["external_id"] == "fm_mark_456"  # mark_id が最優先
        assert r["record_type"] == "movie"
        assert r["title"] == "インターステラー"
        assert r["rating"] == 4.5
        assert r["status"] == "watched"
        assert r["author"] is None
        assert r["event_date"] is None
        p = r["payload"]
        assert p["movie_id"] == "123"
        assert p["mark_id"] == "456"
        assert p["review_id"] == "789"
        assert p["review"] == "とても良かった&泣いた"  # タグ除去+エンティティ復元+続きを読む除去
        assert p["year"] == 2014
        assert p["source_url"] == "https://filmarks.com/movies/123/reviews/789"
        assert p["collected_at"]  # 形式はモジュールにより異なるが必ず付く

    def test_no_rating_dash(self, mod):
        html = card('<a href="/movies/1?mark_id=2">x</a><div class="c-rating__score">-</div>')
        assert mod.parse_cards(html, "https://filmarks.com")[0]["rating"] is None

    def test_title_without_year_span(self, mod):
        html = card(
            '<h3 class="c-content-card__title"><a href="/movies/1?mark_id=2">タイトルのみ</a></h3>'
        )
        r = mod.parse_cards(html, "https://filmarks.com")[0]
        assert r["title"] == "タイトルのみ"
        assert r["payload"]["year"] is None

    def test_external_id_fallback_review_then_movie(self, mod):
        html = card('<a href="/movies/10"></a><a href="/reviews/20"></a>')
        assert mod.parse_cards(html, "https://filmarks.com")[0]["external_id"] == "fm_review_20"

        html = card('<a href="/movies/10"></a>')
        r = mod.parse_cards(html, "https://filmarks.com")[0]
        assert r["external_id"] == "fm_movie_10"
        assert r["payload"]["source_url"] == "https://filmarks.com/movies/10"

    def test_chunk_without_movie_link_skipped(self, mod):
        assert mod.parse_cards(card("<p>no link</p>"), "https://filmarks.com") == []

    def test_no_cards(self, mod):
        assert mod.parse_cards("<html><body>empty</body></html>", "https://filmarks.com") == []


@pytest.mark.parametrize("mod", MODULES)
def test_max_page(mod):
    html = (
        '<a href="/users/ojimpo?page=2">2</a>'
        '<a href="/users/ojimpo?page=5">5</a>'
        '<a href="/users/other?page=9">other user</a>'
    )
    assert mod.max_page(html, "ojimpo") == 5
    assert mod.max_page("<html></html>", "ojimpo") == 1


@pytest.mark.parametrize("mod", MODULES)
def test_strip_tags(mod):
    assert mod.strip_tags("<b>太字</b> と  <i>斜体</i>") == "太字 と 斜体"
    assert mod.strip_tags("a&amp;b") == "a&b"
    assert mod.strip_tags("  ") is None
    assert mod.strip_tags("") is None
    assert mod.strip_tags(None) is None


class TestExtractMovieJsonld:
    def test_finds_movie_block(self):
        html = (
            '<script type="application/ld+json">{"@type": "WebSite"}</script>'
            '<script type="application/ld+json">{"@type": "Movie", "name": "M"}</script>'
        )
        assert delta.extract_movie_jsonld(html) == {"@type": "Movie", "name": "M"}

    def test_invalid_json_skipped(self):
        html = (
            '<script type="application/ld+json">{broken</script>'
            '<script type="application/ld+json">{"@type": "Movie"}</script>'
        )
        assert delta.extract_movie_jsonld(html) == {"@type": "Movie"}

    def test_none_when_absent(self):
        assert delta.extract_movie_jsonld("<html></html>") is None


def test_iso_date_jp():
    import sync_common
    assert sync_common.iso_date_jp("2026/03/10") == "2026-03-10T00:00:00+09:00"
    assert sync_common.iso_date_jp("2026/3/1") == "2026-03-01T00:00:00+09:00"
    assert sync_common.iso_date_jp("日付なし") is None
    assert sync_common.iso_date_jp(None) is None
