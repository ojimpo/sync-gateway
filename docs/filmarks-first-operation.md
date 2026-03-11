# Filmarks 初運用手順（OpenClaw Browser Relay → sync-gateway）

この資料は、Filmarks 取り込みの初回運用手順をまとめたものです。

## 0. 前提

- sync-gateway が起動済み
- `.env` に `GATEWAY_API_KEY` 設定済み
- OpenClaw Browser Relay が使える
- Filmarks にログインできる

---

## 1. Gateway 健全性確認

```bash
curl -sS http://localhost:18000/healthz
# => {"status":"ok"}
```

LAN 運用時は `http://gateway.arigato-nas/healthz` を使用。

---

## 2. source 確認 / 登録（初回のみ）

```bash
curl -sS http://gateway.arigato-nas/api/v1/sources | jq .
```

`filmarks` が無ければ登録:

```bash
curl -X POST http://gateway.arigato-nas/api/v1/sources/register \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <GATEWAY_API_KEY>' \
  -d '{"slug":"filmarks","display_name":"Filmarks"}'
```

---

## 3. Filmarks 実データ投入フロー

1. Browser Relay で Filmarks にログイン
2. 鑑賞記録一覧を取得
3. 正規化して `POST /api/v1/ingest/events`
4. `GET /api/v1/records?source=filmarks&limit=20` で確認

---

## 4. ingest フォーマット（movie）

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
        "year": 2024
      }
    }
  ]
}
```

---

## 5. 失敗時のチェック順

1. `/healthz` が生きているか
2. `filmarks` source が登録済みか
3. POST/PATCH に Bearer が付いているか
4. payload 型が契約通りか（特に `records`）
5. `records` に保存されているか

---

## 6. 注意点

- バッチ上限は 500 件
- 初回は少件数（5〜20件）で試験投入
- 重複防止のため `external_id` は安定した値（作品IDなど）を使う
