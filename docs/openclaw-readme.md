# OpenClaw連携README（arigato-gateway向け）

このドキュメントは、OpenClaw（Pi）から arigato-gateway を使って
読書メーター / Filmarks などのデータを投入する手順をまとめたものです。

## OpenClaw向け最短手順（これだけで投入可能）

1. `GET http://<server-ip>:18000/healthz` が `ok` を返すことを確認
2. `bookmeter` / `filmarks` を `/api/v1/sources/register` で登録（初回のみ）
3. Browser Relayで取得した結果を下の ingest フォーマットで `/api/v1/ingest/events` にPOST
4. `/api/v1/records` と管理画面で反映確認

### OpenClawへ渡すコピペ用プロンプト

```text
Browser Relayで対象サイトからデータを取得し、arigato-gatewayへ投入してください。
- Gateway API: http://<server-ip>:18000
- 事前確認: GET /healthz
- source登録(初回): POST /api/v1/sources/register (bookmeter, filmarks)
- 投入先: POST /api/v1/ingest/events
- 取得失敗項目は null で可
- 投入後: GET /api/v1/records?limit=20 で確認
```

---

## 前提

- arigato-gateway が起動済み
  - API: `http://<server-ip>:18000`
  - Admin: `http://<server-ip>:15173`
- OpenClaw側で Browser Relay が利用可能
- スクレイピングは OpenClaw 側で実施し、gatewayには正規化データを送る

---

## 1) ソース登録（初回のみ）

### 読書メーター

```bash
curl -X POST http://<server-ip>:18000/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -d '{"slug":"bookmeter","display_name":"読書メーター"}'
```

### Filmarks

```bash
curl -X POST http://<server-ip>:18000/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -d '{"slug":"filmarks","display_name":"Filmarks"}'
```

---

## 2) データ投入（ingest）

```bash
curl -X POST http://<server-ip>:18000/api/v1/ingest/events \
  -H 'Content-Type: application/json' \
  -d '{
    "records": [
      {
        "source_slug": "bookmeter",
        "record_type": "book",
        "external_id": "bm_123",
        "title": "サンプル書籍",
        "author": "著者名",
        "rating": 4.0,
        "status": "read",
        "event_date": "2026-03-10T00:00:00+09:00",
        "payload": {
          "source_url": "https://bookmeter.com/..."
        }
      }
    ]
  }'
```

---

## 3) 反映確認

### APIで確認

```bash
curl http://<server-ip>:18000/api/v1/records?limit=20
```

### UIで確認

- `http://<server-ip>:15173`
- Overview / Runs / Sources / Records で可視確認

---

## 4) Browser Relay運用のコツ

- 取得項目はまず最小限（title, rating, date）
- 不安定なDOMセレクタ依存を避ける
- 取れなかった値は null 許容で投入
- payload に原文URLを残して追跡可能にする

---

## 5) 失敗時のトラブルシュート

1. `GET /healthz` が `{"status":"ok"}` か
2. sourceが登録済みか（`GET /api/v1/sources`）
3. payloadの型がAPI契約に沿っているか
4. `GET /api/v1/records` に保存されているか

---

## 6) セキュリティ運用（現状）

- 内部ネットワーク限定
- 認証なし（MVP）
- 外部公開しない

将来外部公開する場合は、最低でも以下を追加:
- API認証（token/JWT）
- 管理UI認証
- 監査ログ
- レート制限
