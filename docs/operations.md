# Operations Guide — OpenClaw → arigato-gateway

## 概要

OpenClaw Browser Relay（ラズパイ等のエッジノードで動作するブラウザ自動化ツール）が定期的にスクレイピングを実行し、正規化したデータを arigato-gateway に HTTP で送信する。

## 認証

書き込み系エンドポイント（POST / PATCH）は Bearer トークン認証で保護されている。
すべての書き込みリクエストに以下のヘッダーを付与すること:

```
Authorization: Bearer <GATEWAY_API_KEY>
```

`GATEWAY_API_KEY` はサーバー側の環境変数で設定する。GET 系は認証不要。

## 標準的なフロー

```
1. (任意) POST /api/v1/runs          — run 開始を記録
2.         POST /api/v1/ingest/events — データをバッチ投入
3. (任意) PATCH /api/v1/runs/{id}    — run 完了/失敗を記録
```

Run ID を使わず ingest のみ呼ぶ簡易モードでも動作する。

## Step 1: ソース登録（初回のみ）

```bash
curl -X POST http://gateway-host:8000/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_API_KEY>' \
  -d '{
    "slug": "bookmeter",
    "display_name": "読書メーター",
    "description": "bookmeter.com からスクレイピングした読書記録"
  }'
```

slug が既に登録されている場合は 409 が返るので、冪等な初期化スクリプトで一度だけ呼ぶ。

## Step 2: Run 開始（任意）

```bash
RUN_ID=$(curl -s -X POST http://gateway-host:8000/api/v1/runs \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_API_KEY>' \
  -d '{"source_id": 1}' | jq '.id')
```

## Step 3: データ投入

```bash
curl -X POST http://gateway-host:8000/api/v1/ingest/events \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_API_KEY>' \
  -d '{
    "records": [
      {
        "source_slug": "bookmeter",
        "run_id": '"$RUN_ID"',
        "record_type": "book",
        "title": "...",
        "author": "...",
        "rating": 4.5,
        "status": "read",
        "event_date": "2026-03-10T10:00:00+09:00",
        "payload": {}
      }
    ]
  }'
```

バッチサイズは最大 500 件。大量データは分割して送る。

レスポンスの `failed` が 0 でない場合は `errors` 配列にメッセージが入っているのでログに残す。

## Step 4: Run 完了を記録（任意）

```bash
curl -X PATCH http://gateway-host:8000/api/v1/runs/$RUN_ID \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_API_KEY>' \
  -d '{
    "status": "success",
    "records_ingested": 42,
    "records_failed": 0
  }'
```

エラー時は `"status": "failed"` と `"error_message": "..."` を設定する。

## エラーハンドリング方針

- ネットワークエラー: リトライを 3 回まで実施（指数バックオフ）
- 401: API キーが無効または未指定。`Authorization: Bearer <key>` ヘッダーを確認。
- 400/422: ペイロードのバリデーション修正が必要。自動リトライ不可。
- 500: ゲートウェイ側の問題。アラートを出して手動調査。
- source_slug 未登録: ingest はスキップして続行。別途 register エンドポイントを呼ぶ。

## データ保持

- SQLite ファイルは `./data/arigato.db` に保存（`volumes` でバインドマウント）
- 定期バックアップは未実装（将来: `sqlite3 arigato.db .dump | gzip > backup.sql.gz` を cron で）

## ヘルスチェック確認

```bash
curl http://gateway-host:8000/healthz
# => {"status":"ok"}
```

Docker コンテナのヘルスチェックも同エンドポイントを使用している。
