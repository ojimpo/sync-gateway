# Filmarks Browser Relay 抽出 → 正規化テンプレ

OpenClaw Browser Relay で取得した Filmarks の生データを
`/api/v1/ingest/events` 向け JSON に変換するためのテンプレ。

---

## 1) 目標フォーマット

```json
{
  "records": [
    {
      "source_slug": "filmarks",
      "external_id": "fm_123456",
      "record_type": "movie",
      "title": "映画タイトル",
      "author": "監督名",
      "rating": 4.0,
      "status": "watched",
      "event_date": "2026-03-10T00:00:00+09:00",
      "payload": {
        "source_url": "https://filmarks.com/movies/123456",
        "review": null,
        "year": 2024,
        "country": null
      }
    }
  ]
}
```

---

## 2) Relay 側で最低限ほしい抽出項目

- `movie_url`（例: `https://filmarks.com/movies/123456`）
- `movie_id`（URLから抽出可）
- `title`
- `director`（取れなければ null）
- `rating_text`（例: `4.0`）
- `watched_date_text`（例: `2026/03/10`）
- `review_text`（取れなければ null）
- `year`（取れなければ null）

---

## 3) マッピングルール

### 固定値
- `source_slug` = `"filmarks"`
- `record_type` = `"movie"`
- `status` = `"watched"`（初期運用）

### external_id
優先順位:
1. `movie_id` がある → `fm_${movie_id}`
2. なければ `movie_url` ハッシュで一意化

### author
- 監督名を `author` に格納（gateway共通スキーマを流用）
- 監督不明なら `null`

### rating
- 数値化できる場合のみ float
- 不明時は `null`

### event_date
- ISO8601に正規化（日時不明なら `T00:00:00+09:00` 補完）

### payload
- `source_url` は必須
- 残りは拡張領域として保持

---

## 4) 変換サンプル

### raw

```json
{
  "movie_url": "https://filmarks.com/movies/123456",
  "movie_id": "123456",
  "title": "Sample Movie",
  "director": "Jane Doe",
  "rating_text": "4.2",
  "watched_date_text": "2026/03/10",
  "review_text": "great",
  "year": 2025
}
```

### normalized

```json
{
  "source_slug": "filmarks",
  "external_id": "fm_123456",
  "record_type": "movie",
  "title": "Sample Movie",
  "author": "Jane Doe",
  "rating": 4.2,
  "status": "watched",
  "event_date": "2026-03-10T00:00:00+09:00",
  "payload": {
    "source_url": "https://filmarks.com/movies/123456",
    "review": "great",
    "year": 2025
  }
}
```

---

## 5) OpenClaw 依頼テンプレ

```text
Filmarksにログインし、鑑賞データを抽出して sync-gateway へ投入してください。

要件:
- Gateway API: http://gateway.arigato-nas
- POST/PATCH は Authorization: Bearer <GATEWAY_API_KEY>
- source_slug は "filmarks"
- record_type は "movie"
- payload に source_url を必ず含める
- 取得失敗項目は null 可
- まず少件数（5〜20件）で試験投入

実行順:
1) GET /healthz
2) GET /api/v1/sources（なければ filmarks を register）
3) POST /api/v1/ingest/events
4) GET /api/v1/records?source=filmarks&limit=20
```
