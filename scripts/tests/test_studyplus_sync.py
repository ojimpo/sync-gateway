"""studyplus_sync の集計・変換ロジックの characterization test。"""
import studyplus_sync as sp


def _feed(date, duration_sec, title, feed_type="study_record"):
    return {
        "feed_type": feed_type,
        "body_study_record": {"record_date": date, "duration": duration_sec, "material_title": title},
    }


class TestAggregateDaily:
    def test_sums_minutes_per_day(self):
        daily = sp.aggregate_daily([
            _feed("2026-07-01", 1800, "数学"),
            _feed("2026-07-01", 600, "英語"),
            _feed("2026-07-02", 3600, "物理"),
        ])
        assert daily["2026-07-01"] == {"minutes": 40, "title": "数学", "sessions": 2}
        assert daily["2026-07-02"] == {"minutes": 60, "title": "物理", "sessions": 1}

    def test_longest_title_wins(self):
        daily = sp.aggregate_daily([
            _feed("2026-07-01", 60, "短い"),
            _feed("2026-07-01", 60, "とても長いタイトル"),
            _feed("2026-07-01", 60, "中くらい"),
        ])
        assert daily["2026-07-01"]["title"] == "とても長いタイトル"

    def test_minutes_rounded_per_record(self):
        # 90秒 → 2分（レコード単位で round してから加算する現仕様）
        daily = sp.aggregate_daily([
            _feed("2026-07-01", 90, "a"),
            _feed("2026-07-01", 90, "b"),
        ])
        assert daily["2026-07-01"]["minutes"] == 4

    def test_skips_records_without_date(self):
        daily = sp.aggregate_daily([_feed(None, 600, "x")])
        assert daily == {}


def test_build_ingest_records():
    daily = {
        "2026-07-02": {"minutes": 30, "title": "英語", "sessions": 1},
        "2026-07-01": {"minutes": 60, "title": "数学", "sessions": 2},
    }
    records = sp.build_ingest_records(daily)
    # 日付昇順・external_id は studyplus_<date>・event_date は JST 0時
    assert [r["external_id"] for r in records] == ["studyplus_2026-07-01", "studyplus_2026-07-02"]
    r = records[0]
    assert r["source_slug"] == "studyplus"
    assert r["record_type"] == "study"
    assert r["title"] == "数学"
    assert r["event_date"] == "2026-07-01T00:00:00+09:00"
    assert r["payload"] == {"minutes": 60}


def test_load_env_value_prefers_process_env(monkeypatch):
    monkeypatch.setenv("STUDYPLUS_CONSUMER_KEY", "from-env")
    assert sp._load_env_value("STUDYPLUS_CONSUMER_KEY") == "from-env"
