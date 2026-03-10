# arigato-gateway

読書メーター・Filmarks などの外部サービスから OpenClaw Browser Relay がスクレイピングした記録データを受け取り、保存・閲覧するためのミドルウェア API と管理ダッシュボード。

## 作った背景

読書メーター・Filmarks には公式 API がない。自分の読書・鑑賞データは自分で手元に持ちたい。しかし、スクレイピングロジックをデータ保存ロジックと混在させると保守が辛い。そこで両者を分離し、スクレイピングは OpenClaw Browser Relay に任せ、このゲートウェイは**正規化ペイロードを受け取って保存するだけ**に集中する設計にした。

## アーキテクチャ

```
OpenClaw Browser Relay (外部)
        │
        │ POST /api/v1/ingest/events
        ▼
 arigato-gateway / backend (FastAPI + SQLite)
        │
        │ REST JSON
        ▼
 arigato-gateway / frontend (React + Vite → nginx)
```

詳細は [docs/architecture.md](docs/architecture.md) を参照。

運用向け補足:
- OpenClaw運用メモ: [docs/openclaw-ops-notes.md](docs/openclaw-ops-notes.md)
- OpenClaw連携手順: [docs/openclaw-readme.md](docs/openclaw-readme.md)

## クイックスタート

### Docker Compose（推奨）

```bash
cp .env.example .env
# .env に GATEWAY_API_KEY を設定（設定しなければ認証なしで動作）
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
DB_PATH=../data/arigato.db uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

### シードデータ投入

```bash
cd backend
python seed.py
```

## 認証

書き込み系エンドポイント（POST / PATCH）は Bearer トークン認証で保護されている。
`.env` に `GATEWAY_API_KEY` を設定すると有効になる。

```bash
# .env
GATEWAY_API_KEY=your-secret-key-here
```

- **認証が必要**: `POST /api/v1/ingest/events`, `POST /api/v1/sources/register`, `POST /api/v1/runs`, `PATCH /api/v1/runs/{id}`
- **認証不要**: `GET /healthz`, `GET /api/v1/sources`, `GET /api/v1/runs`, `GET /api/v1/records`（管理画面が使用するため）
- `GATEWAY_API_KEY` が空または未設定の場合は認証なしで動作（開発環境用）

## curl サンプル（ingest）

ソースを先に登録してから ingest する。`GATEWAY_API_KEY` を設定している場合は `-H 'Authorization: Bearer <key>'` を付ける。

```bash
# 1. ソース登録
curl -X POST http://localhost:18000/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{"slug":"bookmeter","display_name":"読書メーター"}'

# 2. レコード投入
curl -X POST http://localhost:18000/api/v1/ingest/events \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer your-secret-key-here' \
  -d '{
    "records": [{
      "source_slug": "bookmeter",
      "record_type": "book",
      "title": "海辺のカフカ",
      "author": "村上春樹",
      "rating": 4.5,
      "status": "read",
      "event_date": "2026-02-14T00:00:00+09:00",
      "payload": {"isbn": "9784167919535"}
    }]
  }'
```

## ファイル構成

```
arigato-gateway/
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
│   ├── seed.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Layout + nav
│   │   ├── api.ts           # Typed fetch helpers
│   │   └── components/
│   │       ├── Overview.tsx
│   │       ├── RunsTable.tsx
│   │       ├── SourcesTable.tsx
│   │       └── RecordsPanel.tsx
│   ├── Dockerfile
│   └── nginx.conf
├── samples/
│   ├── bookmeter_payload.json
│   └── filmarks_payload.json
├── data/                    # SQLite (gitignored)
├── docs/
│   ├── architecture.md
│   ├── api-contract.md
│   ├── operations.md
│   └── meetings/
│       ├── 2026-03-10-minutes.md
│       └── 2026-03-10-transcript.md
├── docker-compose.yml
└── .env.example
```
