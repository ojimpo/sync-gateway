"""filmarks 系スクリプトの HTML パース処理の characterization test。

パース実装は filmarks_common に集約されている。delta / slow スクリプトが
同じ実装を使っていることも配線テストで担保する。
"""
import filmarks_common as fc
import filmarks_sync_delta as delta
import filmarks_sync_slow as slow
import sync_common


def test_scripts_share_common_implementation():
    assert delta.parse_cards is fc.parse_cards
    assert slow.parse_cards is fc.parse_cards
    assert delta.max_page is fc.max_page
    assert slow.max_page is fc.max_page
    assert delta.extract_movie_jsonld is fc.extract_movie_jsonld


def card(inner: str) -> str:
    return f'<div class="c-content-card">{inner}</div>'

FULL_CARD = card(
    '<h3 class="c-content-card__title">'
    '<a href="/movies/123?mark_id=456">インターステラー<span>(2014年製作の映画)</span></a></h3>'
    '<div class="c-rating__score">4.5</div>'
    '<p class="c-content-card__review">とても良かった&amp;泣いた>>続きを読む</p>'
    '<a href="/movies/123/reviews/789">review</a>'
)


class TestParseCards:
    def test_full_card(self):
        recs = fc.parse_cards(FULL_CARD, "https://filmarks.com")
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
        assert p["collected_at"]

    def test_no_rating_dash(self):
        html = card('<a href="/movies/1?mark_id=2">x</a><div class="c-rating__score">-</div>')
        assert fc.parse_cards(html, "https://filmarks.com")[0]["rating"] is None

    def test_full_card_hash_mark_format(self):
        """2026-03-25 に Filmarks が変えた新形式 (#mark-<id>)。

        旧形式しか見ていなかったため全カードが弾かれ、約5ヶ月間 parsed=0 の
        まま無音で止まった。external_id は旧形式と同じ体系でないと、
        復旧時に既存レコードと重複する。
        """
        html = card(
            '<h3 class="c-content-card__title">'
            '<a href="/movies/123#mark-456">インターステラー<span>(2014年製作の映画)</span></a></h3>'
            '<div class="c-rating__score">4.5</div>'
            '<a href="/movies/123/reviews/789">review</a>'
        )
        r = fc.parse_cards(html, "https://filmarks.com")[0]
        assert r["external_id"] == "fm_mark_456"
        assert r["payload"]["movie_id"] == "123"
        assert r["payload"]["mark_id"] == "456"
        assert r["title"] == "インターステラー"
        assert r["rating"] == 4.5

    def test_both_mark_id_formats_yield_same_external_id(self):
        old = card('<a href="/movies/123?mark_id=456">x</a>')
        new = card('<a href="/movies/123#mark-456">x</a>')
        assert (
            fc.parse_cards(old, "https://filmarks.com")[0]["external_id"]
            == fc.parse_cards(new, "https://filmarks.com")[0]["external_id"]
        )

    def test_live_markup_shape_2026_08(self):
        """2026-08 時点の実ページから採った並びをそのまま通す回帰テスト。

        カード内には作品リンクの他に /reviews/ や /login?mark_id=... も並ぶ。
        先頭の作品リンクを拾えていること（/login 側を誤って拾わないこと）を見る。
        """
        html = card(
            '<div class="c-content-card__left">'
            '<a href="/movies/118757#mark-216980657"><img src="x.jpg"></a></div>'
            '<div class="c-content-card__right">'
            '<h3 class="c-content-card__title">'
            '<a href="/movies/118757#mark-216980657">秒速5センチメートル'
            '<span>(2025年製作の映画)</span></a></h3>'
            '<div class="c-rating c-rating--50"><div class="c-rating__star"></div>'
            '<div class="c-rating__score">5.0</div></div>'
            '<p class="c-content-card__review">よかった&gt;&gt;続きを読む</p>'
            '<a href="/movies/118757/reviews/216980657">review</a>'
            '<a href="/login?mark_id=216980657&amp;movie_id=118757">login</a>'
            '</div>'
        )
        recs = fc.parse_cards(html, "https://filmarks.com")
        assert len(recs) == 1
        r = recs[0]
        assert r["external_id"] == "fm_mark_216980657"
        assert r["title"] == "秒速5センチメートル"
        assert r["rating"] == 5.0
        assert r["payload"]["year"] == 2025
        assert r["payload"]["source_url"] == "https://filmarks.com/movies/118757/reviews/216980657"

    def test_title_without_year_span(self):
        html = card(
            '<h3 class="c-content-card__title"><a href="/movies/1?mark_id=2">タイトルのみ</a></h3>'
        )
        r = fc.parse_cards(html, "https://filmarks.com")[0]
        assert r["title"] == "タイトルのみ"
        assert r["payload"]["year"] is None

    def test_external_id_fallback_review_then_movie(self):
        html = card('<a href="/movies/10"></a><a href="/reviews/20"></a>')
        assert fc.parse_cards(html, "https://filmarks.com")[0]["external_id"] == "fm_review_20"

        html = card('<a href="/movies/10"></a>')
        r = fc.parse_cards(html, "https://filmarks.com")[0]
        assert r["external_id"] == "fm_movie_10"
        assert r["payload"]["source_url"] == "https://filmarks.com/movies/10"

    def test_chunk_without_movie_link_skipped(self):
        assert fc.parse_cards(card("<p>no link</p>"), "https://filmarks.com") == []

    def test_no_cards(self):
        assert fc.parse_cards("<html><body>empty</body></html>", "https://filmarks.com") == []


def test_max_page():
    html = (
        '<a href="/users/ojimpo?page=2">2</a>'
        '<a href="/users/ojimpo?page=5">5</a>'
        '<a href="/users/other?page=9">other user</a>'
    )
    assert fc.max_page(html, "ojimpo") == 5
    assert fc.max_page("<html></html>", "ojimpo") == 1


def test_strip_tags():
    assert sync_common.strip_tags("<b>太字</b> と  <i>斜体</i>") == "太字 と 斜体"
    assert sync_common.strip_tags("a&amp;b") == "a&b"
    assert sync_common.strip_tags("  ") is None
    assert sync_common.strip_tags("") is None
    assert sync_common.strip_tags(None) is None


class TestExtractMovieJsonld:
    def test_finds_movie_block(self):
        html = (
            '<script type="application/ld+json">{"@type": "WebSite"}</script>'
            '<script type="application/ld+json">{"@type": "Movie", "name": "M"}</script>'
        )
        assert fc.extract_movie_jsonld(html) == {"@type": "Movie", "name": "M"}

    def test_invalid_json_skipped(self):
        html = (
            '<script type="application/ld+json">{broken</script>'
            '<script type="application/ld+json">{"@type": "Movie"}</script>'
        )
        assert fc.extract_movie_jsonld(html) == {"@type": "Movie"}

    def test_none_when_absent(self):
        assert fc.extract_movie_jsonld("<html></html>") is None


def test_iso_date_jp():
    assert sync_common.iso_date_jp("2026/03/10") == "2026-03-10T00:00:00+09:00"
    assert sync_common.iso_date_jp("2026/3/1") == "2026-03-01T00:00:00+09:00"
    assert sync_common.iso_date_jp("日付なし") is None
    assert sync_common.iso_date_jp(None) is None


# ── スクレイプ破損の検知 ──────────────────────────────────────────────────────
#
# 2026-03-25 の HTML 変更で parsed=0 が5ヶ月続いたが、HTTP は 200 で
# 「新着なし」と区別がつかず、gateway にも run が残らないので誰も気付けなかった。


class TestZeroParseStreak:
    def test_increments_while_nothing_parses(self):
        assert delta.next_zero_parse_streak(None, 0) == 1
        assert delta.next_zero_parse_streak(1, 0) == 2
        assert delta.next_zero_parse_streak(7, 0) == 8

    def test_resets_when_anything_parses(self):
        assert delta.next_zero_parse_streak(9, 36) == 0
        assert delta.next_zero_parse_streak(None, 1) == 0

    def test_alert_threshold_boundary(self):
        """一時的な失敗では鳴らさず、続いたら鳴る。"""
        streak = 0
        fired = []
        for _ in range(4):
            streak = delta.next_zero_parse_streak(streak, 0)
            fired.append(streak >= delta.ZERO_PARSE_ALERT_AFTER)
        assert fired == [False, False, True, True]


class TestReportBrokenScrape:
    def _stub(self, calls):
        def fake(base, path, method="GET", payload=None, api_key=None):
            calls.append((method, path, payload))
            if path == "/api/v1/sources":
                return 200, [{"id": 2, "slug": "filmarks"}]
            if path == "/api/v1/runs":
                return 201, {"id": 999}
            return 200, {}
        return fake

    def test_registers_failed_run(self, monkeypatch):
        calls = []
        monkeypatch.setattr(delta, "gateway_request", self._stub(calls))
        delta.report_broken_scrape("http://gw", "key", streak=3, pages=3)

        assert ("POST", "/api/v1/runs", {"source_id": 2}) in calls
        patch = [c for c in calls if c[0] == "PATCH"]
        assert len(patch) == 1
        assert patch[0][1] == "/api/v1/runs/999"
        assert patch[0][2]["status"] == "failed"
        assert "3回連続" in patch[0][2]["error_message"]

    def test_survives_gateway_errors(self, monkeypatch):
        """通報に失敗しても同期本体を落とさない。

        gateway_request は 4xx/5xx で HTTPError を投げる（返り値でコードを
        返さない）ので、通信・認証エラーは例外として飛んでくる。
        """
        def boom(*a, **k):
            raise OSError("gateway down")
        monkeypatch.setattr(delta, "gateway_request", boom)
        delta.report_broken_scrape("http://gw", "key", streak=3, pages=3)  # 例外を投げない

    def test_no_run_when_source_missing(self, monkeypatch):
        calls = []
        def fake(base, path, method="GET", payload=None, api_key=None):
            calls.append((method, path, payload))
            return 200, [{"id": 1, "slug": "bookmeter"}]
        monkeypatch.setattr(delta, "gateway_request", fake)
        delta.report_broken_scrape("http://gw", "key", streak=3, pages=3)
        assert [c for c in calls if c[0] == "POST"] == []


class TestExtractReviewDatetime:
    """一覧カードに日付が無いので、鑑賞日はレビュー詳細ページから取る。

    公開日フォールバックだと「公開が何年も前の作品を今日観た」ケースで
    何年も過去に記録されてしまう（秒速5センチメートルで7ヶ月ずれた）。
    """

    def test_extracts_jst_iso(self):
        html = '<time class="c-media__date" datetime="2026-05-06 03:57">2026/05/06 03:57</time>'
        assert fc.extract_review_datetime(html) == "2026-05-06T03:57:00+09:00"

    def test_accepts_iso_separator(self):
        html = '<time class="c-media__date" datetime="2026-05-06T03:57">x</time>'
        assert fc.extract_review_datetime(html) == "2026-05-06T03:57:00+09:00"

    def test_ignores_other_time_elements(self):
        html = (
            '<time datetime="2020-01-01 00:00">無関係</time>'
            '<time class="c-media__date" datetime="2026-05-06 03:57">本命</time>'
        )
        assert fc.extract_review_datetime(html) == "2026-05-06T03:57:00+09:00"

    def test_none_when_absent(self):
        assert fc.extract_review_datetime("<html></html>") is None
        assert fc.extract_review_datetime('<time class="other" datetime="2026-05-06 03:57">x</time>') is None


class TestFetchReviewDate:
    class _Resp:
        def __init__(self, text): self.text = text
        def raise_for_status(self): pass

    def test_returns_posted_date(self, monkeypatch):
        class Sess:
            def get(self, url, timeout=None):
                assert url == "https://filmarks.com/movies/118757/reviews/216980657"
                return TestFetchReviewDate._Resp(
                    '<time class="c-media__date" datetime="2026-05-06 03:57">x</time>'
                )
        assert delta.fetch_review_date(Sess(), "118757", "216980657") == "2026-05-06T03:57:00+09:00"

    def test_returns_none_on_error(self):
        """取得に失敗しても例外を投げない（公開日フォールバックに委ねる）。"""
        class Sess:
            def get(self, url, timeout=None):
                raise OSError("boom")
        assert delta.fetch_review_date(Sess(), "1", "2") is None
