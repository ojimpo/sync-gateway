# Bookmeter 初運用手順（OpenClaw Browser Relay → sync-gateway）

この資料は、初回運用時に迷わないための実行手順をまとめたものです。

## 0. 前提

- sync-gateway が起動済み
- `.env` に `GATEWAY_API_KEY` 設定済み
- OpenClaw Browser Relay が使える
- Bookmeter にログインできる

---

## 1. Gateway 健全性確認

```bash
curl -sS http://localhost:18000/healthz
# => {"status":"ok"}
```

LAN 運用時は `http://gateway.arigato-nas/healthz` を使う。

---

## 2. 初回スモークテスト（推奨）

以下のスクリプトで、`health → source確認/登録 → ingest → records確認` を一括実行できます。

```bash
cd ~/dev/sync-gateway
./scripts/gateway_first_run_check.sh
# または
./scripts/gateway_first_run_check.sh http://gateway.arigato-nas samples/bookmeter_first_run_payload.json
```

---

## 3. Bookmeter 実データ投入フロー

1. Browser Relay で Bookmeter にログイン
2. 読了一覧（必要なら読書中も）を取得
3. 下記フォーマットに正規化
4. `POST /api/v1/ingest/events` へ投入
5. `GET /api/v1/records?source=bookmeter&limit=20` で確認

### 推奨レコード形式

```json
{
  "source_slug": "bookmeter",
  "external_id": "bm_<book-id or URL-hash>",
  "record_type": "book",
  "title": "本のタイトル",
  "author": "著者名",
  "rating": 4.0,
  "status": "read",
  "event_date": "2026-03-10T00:00:00+09:00",
  "payload": {
    "source_url": "https://bookmeter.com/...",
    "isbn": null,
    "review": null
  }
}
```

---

## 4. APIキー運用ルール（推奨）

- APIキーは 1Password（OpenClaw vault）を正本にする
- 平文でチャットに貼らない
- 通常運用は `.env` 参照
- キー更新時のみ `.env` を更新して backend を再起動

---

## 5. 失敗時のチェック順

1. `/healthz` が生きているか
2. `bookmeter` source が登録済みか
3. Bearer ヘッダーが付いているか（POST/PATCH）
4. payload が契約に沿っているか（特に `records` 配列）
5. `records` に保存されているか

---

## 6. 注意点

- バッチ上限は 500 件（超える場合は分割）
- `run_id` は任意（初回はなしでも可）
- `.env` 更新後は backend 再起動を推奨
