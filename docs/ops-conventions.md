# Operations Conventions

このドキュメントは、運用ルール（命名・同期方針・公開前手順）を一元管理するための基準です。

## 1) Discord命名ルール

### カテゴリ
- すべてのカテゴリ名は **先頭に絵文字** を付ける。
- 例: `🏠 main`, `📱 app`, `📚 sync-gateway`

### チャンネル
- 原則として **絵文字なし** の kebab-case。
- 例: `sync-gateway-bookmeter`, `rate-limit`
- 例外: `🏠 main` 配下の3チャンネルは末尾絵文字を維持
  - `red🔴`
  - `blue🔵`
  - `green🟢`

### セッション管理
- テーマが大きくなったら `🟦 active-sessions` 配下に**セッションチャンネルを切り出す**。
- 切り出し時は、main（`red🔴/blue🔵/green🟢`）には要点だけ残し、詳細作業はセッションチャンネル側で実施する。
- セッションを完了したら `✅ completed-sessions` へ移動。
- 完了時はセッションチャンネル名の先頭に完了マークを付ける（必要時）。

### mainチャンネルのリセット運用
- セッション切り出し後、mainチャンネルは「次の話題の待機状態」に戻す。
- mainには以下のみ残す:
  - 現在進行中セッションへのリンク
  - 直近の決定事項（短い要約）
- 長文ログや実装詳細は main に残さない（可読性維持）。
- これを**セッションリセット**として定常運用する。

---

## 2) Bookmeter/Filmarks 同期ルール

- 初回は低速で全件同期（ランダム待機あり）
- 以降は差分同期
- 欠損は許容し、`payload` に拡張情報を保持
- 弾かれた場合は Browser Relay をフォールバックとして利用

### Run 統計カラムの仕様
- `records_processed`: 処理したレコードの総数（新規 + 更新）
- `records_created`: `external_id` が新規だったレコード数
- `records_updated`: `external_id` が既存で上書きしたレコード数
- `records_failed`: エラーでスキップしたレコード数
- ingest 時にゲートウェイ側で自動インクリメント。PATCH で上書きは不要。

### external_id 方針（イベント単位）
- 形式: `<source_slug>:<event_key>` を推奨
- Bookmeter: `bookmeter:review:<review_id>` 相当
- レビューIDが取れない場合は `book_id + date + status` でフォールバック

---

## 3) 公開前ルール

- 公開名は `sync-gateway` 方針
- `scraping-gateway` は心象面の理由で採用しない
- `.env` / APIキー /個人データは公開前に必ず除去
- 詳細チェックは `docs/github-publish-checklist.md` を参照

---

## 4) 変更管理

- 重要な運用判断は `docs/decisions.md` に記録
- 本ファイルは「現行ルールの正本（single source of truth）」として扱う
