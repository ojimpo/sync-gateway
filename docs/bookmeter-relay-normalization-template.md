# Bookmeter Browser Relay 抽出 → 正規化テンプレ

このドキュメントは、OpenClaw Browser Relay で取得した Bookmeter の生データを
`/api/v1/ingest/events` 用の正規化 JSON に変換するためのテンプレです。

---

## 1) 目標フォーマット（ingest request body）

```json
{
  "records": [
    {
      "source_slug": "bookmeter",
      "external_id": "bm_123456",
      "record_type": "book",
      "title": "本のタイトル",
      "author": "著者名",
      "rating": 4.0,
      "status": "read",
      "event_date": "2026-03-10T00:00:00+09:00",
      "payload": {
        "source_url": "https://bookmeter.com/books/123456",
        "isbn": null,
        "review": null
      }
    }
  ]
}
```

---

## 2) Relay 側で最低限ほしい抽出項目

各書籍について以下を取る:

- `book_url`（例: `https://bookmeter.com/books/123456`）
- `book_id`（URLから抽出で可）
- `title`
- `author`
- `rating_text`（例: `★4` / `4.0` / 未設定）
- `status_text`（例: `読んだ`, `読んでる`）
- `event_date_text`（例: `2026/03/10`）
- `review_text`（取れなければ null）
- `isbn`（取れなければ null）

---

## 3) マッピングルール

### 固定値
- `source_slug` = `"bookmeter"`
- `record_type` = `"book"`

### external_id
優先順位:
1. `book_id` がある → `bm_${book_id}`
2. なければ `book_url` のハッシュ等で一意化

### rating
- 数値化できる場合のみ `0..10` の float
- Bookmeter の 5段階想定ならそのまま `0..5` でも可（契約上は `0..10` まで許容）
- 取れなければ `null`

### status
例:
- `読んだ` → `read`
- `読んでる` → `reading`
- 不明 → 元文字列 or `null`

### event_date
- 可能なら ISO8601 (`YYYY-MM-DDTHH:mm:ss+09:00`)
- 日付だけなら `T00:00:00+09:00` を補う
- 取れなければ `null`

### payload
最低限、追跡できるように `source_url` は入れる:

```json
"payload": {
  "source_url": "...",
  "isbn": null,
  "review": null
}
```

---

## 4) 変換サンプル（raw → normalized）

### raw（Relay抽出の想定）

```json
{
  "book_url": "https://bookmeter.com/books/123456",
  "book_id": "123456",
  "title": "サンプル本",
  "author": "著者A",
  "rating_text": "4.0",
  "status_text": "読んだ",
  "event_date_text": "2026/03/10",
  "review_text": "面白かった",
  "isbn": null
}
```

### normalized（ingest record）

```json
{
  "source_slug": "bookmeter",
  "external_id": "bm_123456",
  "record_type": "book",
  "title": "サンプル本",
  "author": "著者A",
  "rating": 4.0,
  "status": "read",
  "event_date": "2026-03-10T00:00:00+09:00",
  "payload": {
    "source_url": "https://bookmeter.com/books/123456",
    "isbn": null,
    "review": "面白かった"
  }
}
```

---

## 5) OpenClaw 依頼テンプレ（コピペ用）

```text
Bookmeterにログインし、読書データを抽出して sync-gateway に投入してください。

要件:
- Gateway API: http://gateway.arigato-nas
- POST/PATCHは Authorization: Bearer <GATEWAY_API_KEY>
- source_slug は "bookmeter"
- record_type は "book"
- 取得失敗項目は null 可
- payload に source_url を必ず残す
- まずは少件数（5〜20件）で試し、成功後に範囲を拡大

実行順:
1) GET /healthz
2) GET /api/v1/sources で bookmeter 確認（なければ register）
3) POST /api/v1/ingest/events
4) GET /api/v1/records?source=bookmeter&limit=20
```

---

## 6) 重複対策（推奨）

初期実装では DB 側に `external_id` のユニーク制約がないため、
再投入時に重複が増える可能性があります。

運用での暫定対策:
- 同一 run 内は `external_id` 重複を除外してから送信
- 差分同期（直近更新のみ）を優先

将来的には以下を検討:
- `(source_id, external_id)` のユニーク制約
- ingest時の upsert
