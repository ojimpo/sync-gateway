# API Contract

Base URL: `http://<host>`（docker-compose の nginx 経由）

- 例（ローカル）: `http://localhost:18000`
- 例（LAN）: `http://gateway.arigato-nas`

OpenAPI UI: `GET /docs`
OpenAPI JSON: `GET /openapi.json`

---

## Health

### `GET /healthz`

```json
200 OK
{ "status": "ok" }
```

---

## Sources

### `GET /api/v1/sources`

登録済みソース一覧を返す。

```json
200 OK
[
  {
    "id": 1,
    "slug": "bookmeter",
    "display_name": "読書メーター",
    "description": "bookmeter.com の読書記録",
    "active": true,
    "created_at": "2026-03-10T00:00:00Z"
  }
]
```

### `POST /api/v1/sources/register`

新しいソースを登録する。`slug` が既存と重複する場合は `409 Conflict`。

**Request body**

```json
{
  "slug": "bookmeter",        // required; pattern: ^[a-z0-9_-]+$
  "display_name": "読書メーター", // required
  "description": "...",       // optional
  "active": true              // optional; default true
}
```

**Response** `201 Created` — SourceOut (上記と同形式)

---

## Runs

### `GET /api/v1/runs?limit=100`

run 履歴を started_at 降順で返す。

```json
200 OK
[
  {
    "id": 1,
    "source_id": 1,
    "status": "success",        // running | success | failed
    "started_at": "2026-03-10T01:00:00Z",
    "finished_at": "2026-03-10T01:00:05Z",
    "records_processed": 42,
    "records_created": 40,
    "records_updated": 2,
    "records_failed": 0,
    "error_message": null
  }
]
```

### `POST /api/v1/runs`

run を開始する（status=running）。`source_id` が存在しない場合は `404`。

```json
{ "source_id": 1 }
```

**Response** `201 Created` — RunOut

### `PATCH /api/v1/runs/{id}`

run を完了 or 失敗させる。

```json
{
  "status": "success",        // success | failed
  "records_failed": 0,
  "error_message": null
}
```

**Response** `200 OK` — RunOut（統計カラムは ingest 時に自動更新されるため、PATCH では `records_*` を指定不要）

---

## Ingest

### `POST /api/v1/ingest/events`

**主要エンドポイント**。1〜500 件のレコードをバッチ投入する。`source_slug` が未登録の場合はそのレコードのみスキップし、他は処理継続。

**Request body**

```json
{
  "records": [
    {
      "source_slug": "bookmeter",        // required; 登録済み slug
      "run_id": 1,                       // optional; run と紐付ける場合
      "external_id": "bm_book_xxx",     // optional; 外部サービスの ID
      "record_type": "book",             // required; book | movie | ...
      "title": "海辺のカフカ",
      "author": "村上春樹",
      "rating": 4.5,                     // optional; 0〜10
      "status": "read",                  // optional; ソース定義の状態値
      "event_date": "2026-02-14T00:00:00+09:00",  // optional; ISO 8601
      "payload": {                       // optional; 任意の追加フィールド
        "isbn": "9784167919535",
        "review": "..."
      }
    }
  ]
}
```

**Response** `202 Accepted`

```json
{
  "accepted": 1,
  "failed": 0,
  "errors": []
}
```

---

## Records

### `GET /api/v1/records?source=&from=&to=&limit=50`

| パラメータ | 型 | 説明 |
|---|---|---|
| `source` | string | ソース slug でフィルター |
| `from` | ISO 8601 datetime | ingested_at の下限 |
| `to` | ISO 8601 datetime | ingested_at の上限 |
| `limit` | int (max 500) | 取得件数 |

**Response** `200 OK`

```json
[
  {
    "id": 1,
    "source_id": 1,
    "run_id": 1,
    "external_id": "bm_book_xxx",
    "record_type": "book",
    "title": "海辺のカフカ",
    "author": "村上春樹",
    "rating": 4.5,
    "status": "read",
    "event_date": "2026-02-14T00:00:00Z",
    "ingested_at": "2026-03-10T01:00:03Z"
  }
]
```

---

## エラーレスポンス

FastAPI のデフォルト形式に準拠:

```json
{ "detail": "エラーメッセージ" }
```

| Status | 意味 |
|---|---|
| 400 / 422 | バリデーションエラー |
| 404 | リソース未存在 |
| 409 | 重複登録（slug conflict） |
| 500 | サーバー内部エラー |
