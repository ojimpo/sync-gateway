# Architecture

## 概要

arigato-gateway は 3 層で構成される。

```
[ OpenClaw Browser Relay ]
          │
          │ HTTP POST /api/v1/ingest/events
          │ (正規化ペイロード: JSON)
          ▼
    [ backend ]
    FastAPI (Python 3.12)
    SQLAlchemy 2 + SQLite
    uvicorn
          │
          │ REST JSON
          ▼
    [ frontend ]
    React 18 + Vite 5 (dev)
    nginx (prod, Docker)
```

## Backend

### 技術選定

| 要素 | 採用 | 理由 |
|---|---|---|
| Framework | FastAPI | 自動 OpenAPI 生成、Pydantic 統合、型安全 |
| ORM | SQLAlchemy 2 (mapped_column) | 型付きモデル、軽量、SQLite 対応 |
| DB | SQLite | シングルノード用途、追加インフラ不要 |
| バリデーション | Pydantic v2 | FastAPI との完全統合 |

### データモデル

```
sources        runs             records          ingest_errors
─────────      ─────────        ─────────────    ─────────────
id (PK)        id (PK)          id (PK)          id (PK)
slug           source_id (FK)   source_id (FK)   run_id (FK)
display_name   status           run_id (FK)      raw_payload (JSON)
description    started_at       external_id      error_message
active         finished_at      record_type      occurred_at
created_at     records_ingested title
               records_failed   author
               error_message    rating
                                status
                                event_date
                                payload (JSON)
                                ingested_at
```

- `records.payload`: ソース固有の追加フィールドを JSON で保持。将来のスキーマ変更に備えた raw 保存。
- `ingest_errors`: バッチ ingest でパース/バリデーションに失敗したレコードのログ。
- `runs`: OpenClaw がひとつの同期セッションを表す。`PATCH /api/v1/runs/{id}` で完了/失敗を記録。

### CORS

`FRONTEND_ORIGIN` 環境変数で指定したオリジンのみ許可。デフォルト `http://localhost:5173`。内部ネットワーク用途のため認証は MVP では省略。

## Frontend

React + Vite で構築した SPA。4 ページ構成:

- **Overview**: 統計カード（合計 runs, 成功率, ingested 件数, アクティブソース数）+ 最近の runs
- **Runs**: 全 run 履歴テーブル（ステータスバッジ、duration 表示）
- **Sources**: 登録済みソース一覧
- **Records**: レコード閲覧（ソースフィルター付き）

ダークテーマ（CSS カスタムプロパティ）、ビルドツール依存なしのインラインスタイルで実装。

### 本番ビルド（Docker）

nginx コンテナが React の静的ビルドをサーブしつつ `/api/*` と `/healthz` を backend にプロキシする。

## セキュリティ

- 内部 LAN 専用。認証なし（MVP）
- CORS で frontend origin のみ許可
- シークレットのコミットなし（`.env.example` のみ）
- 将来: Bearer トークン認証、または Tailscale/WireGuard による境界防御
