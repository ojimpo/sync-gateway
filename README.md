# sync-gateway

公式 API のない外部サービス（読書メーター・Filmarks など）から収集したデータを受け取り、保存・閲覧するためのミドルウェア API と管理ダッシュボード。データ収集エージェントとして [OpenClaw Browser Relay](https://github.com/kouki-dan/openclaw) を使用している。

## 作った背景

読書メーター・Filmarks には公式 API がない。自分の読書・鑑賞データは自分で手元に置きたい。しかし、データ収集ロジックと保存ロジックを混在させると保守が辛い。そこで両者を完全に分離した。

- データ収集・正規化は **OpenClaw Browser Relay**（外部エージェント）が担当
- このゲートウェイは**正規化済みペイロードを受け取って保存するだけ**に集中
- API は汎用的な設計で、今後どのサービスからのデータでも受け入れ可能

## アーキテクチャ

```
OpenClaw Browser Relay（外部エージェント）
        │
        │ POST /api/v1/ingest/events（正規化 JSON）
        ▼
  sync-gateway / backend
  FastAPI + SQLAlchemy + SQLite
        │
        │ REST JSON
        ▼
  sync-gateway / frontend
  React + Vite → nginx
```

詳細は [docs/architecture.md](docs/architecture.md) を参照。

### データモデル設計の肝

- **sources**: サービスごとに `slug`（例: `bookmeter`, `filmarks`）で識別
- **runs**: 同期セッション単位の記録（`processed` / `created` / `updated` / `failed` でカウント分解）
- **records**: `external_id` を持つ場合は upsert で重複防止。`payload` に JSON 拡張フィールドを保持
- **ingest_errors**: バッチ内の部分失敗ログ（全件ロールバックせず継続）

## クイックスタート

```bash
cp .env.example .env
# .env に GATEWAY_API_KEY を設定（空のままでも認証なしで動作）
mkdir -p data
docker compose up --build
```

- 管理画面: http://localhost:15173
- API: http://localhost:18000
- OpenAPI: http://localhost:18000/docs

### ローカル開発

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DB_PATH=../data/sync-gateway.db uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**DBマイグレーション**

```bash
cd backend
alembic upgrade head
```

**シードデータ投入**

```bash
cd backend
python seed.py
```

**テスト**

backend API と同期スクリプトのパース処理に characterization test がある。

```bash
pip install -r backend/requirements-dev.txt

# 全テスト
python3 -m pytest backend/tests scripts/tests

# backend API のみ / スクリプトのみ
python3 -m pytest backend/tests
python3 -m pytest scripts/tests
```

## 認証

書き込み系エンドポイント（POST / PATCH）は Bearer トークンで保護。

```bash
# .env
GATEWAY_API_KEY=your-secret-key-here
```

| エンドポイント | 認証 |
|---|---|
| `POST /api/v1/ingest/events` | 必要 |
| `POST /api/v1/sources/register` | 必要 |
| `POST /api/v1/runs`, `PATCH /api/v1/runs/{id}` | 必要 |
| `GET /healthz`, `GET /api/v1/sources`, `GET /api/v1/runs`, `GET /api/v1/records` | 不要 |

`GATEWAY_API_KEY` が空または未設定の場合は認証なし（開発環境用）。

## curl サンプル

```bash
# ソース登録（初回のみ）
curl -X POST http://localhost:18000/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{"slug":"bookmeter","display_name":"読書メーター"}'

# Run 開始（任意）
RUN_ID=$(curl -s -X POST http://localhost:18000/api/v1/runs \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{"source_id": 1}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# データ投入
curl -X POST http://localhost:18000/api/v1/ingest/events \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{
    "records": [{
      "source_slug": "bookmeter",
      "run_id": '"$RUN_ID"',
      "external_id": "bm_book_12345",
      "record_type": "book",
      "title": "海辺のカフカ",
      "author": "村上春樹",
      "rating": 4.5,
      "status": "read",
      "event_date": "2026-02-14T00:00:00+09:00",
      "payload": {"isbn": "9784167919535"}
    }]
  }'

# Run 完了を記録（任意）
curl -X PATCH http://localhost:18000/api/v1/runs/$RUN_ID \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{"status": "success"}'
```

`external_id` が同じレコードを再投入すると upsert（差分更新）される。`payload` フィールドはマージされる。

## Run 統計カラム

| カラム | 内容 |
|---|---|
| `records_processed` | 試行総数（created + updated + failed） |
| `records_created` | 新規 insert 成功件数 |
| `records_updated` | upsert 更新成功件数 |
| `records_failed` | エラー件数（unknown source / 例外） |

## 初回運用チェック（スクリプト）

```bash
./scripts/gateway_first_run_check.sh
# または
./scripts/gateway_first_run_check.sh http://<your-host> samples/bookmeter_first_run_payload.json
```

前提: `.env` に `GATEWAY_API_KEY` が設定済み・API が起動済み。

## ファイル構成

```
sync-gateway/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, router mount
│   │   ├── auth.py          # Bearer token 認証
│   │   ├── database.py      # SQLAlchemy engine / session
│   │   ├── models.py        # ORM: sources, runs, records, ingest_errors
│   │   ├── schemas.py       # Pydantic I/O models
│   │   └── routers/
│   │       ├── health.py
│   │       ├── sources.py
│   │       ├── runs.py
│   │       ├── ingest.py
│   │       └── records.py
│   ├── migrations/          # Alembic マイグレーション
│   ├── tests/               # API characterization tests (pytest)
│   ├── seed.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Layout + nav
│   │   ├── api.ts           # Typed fetch helpers
│   │   └── components/
│   │       ├── Overview.tsx
│   │       ├── RunsTable.tsx
│   │       ├── SourcesTable.tsx
│   │       ├── RecordsPanel.tsx
│   │       └── Table.tsx    # 共通テーブルUI
│   ├── Dockerfile
│   └── nginx.conf
├── samples/
│   └── bookmeter_first_run_payload.json
├── scripts/
│   ├── sync_common.py       # 同期スクリプト共通ヘルパー
│   ├── filmarks_common.py   # Filmarks HTMLパース共通処理
│   ├── bookmeter_*.py / filmarks_*.py / studyplus_sync.py  # 各サービスの同期スクリプト
│   ├── run_sync_*.sh        # cron 用ラッパー
│   ├── tests/               # スクリプトの characterization tests
│   └── gateway_first_run_check.sh
├── data/                    # SQLite（gitignore 済み）
├── docs/
│   ├── architecture.md
│   ├── api-contract.md
│   ├── operations.md
│   └── decisions.md
├── docker-compose.yml
└── .env.example
```

## 将来の展望

- 新しいサービスへの対応：source slug を追加し、OpenClaw 側に抽出ロジックを書くだけ
- Webhook 通知（同期完了時に Discord 等へ）
- CSV / JSON エクスポートエンドポイント
- 監査ログの強化・Tailscale/WireGuard による境界防御
