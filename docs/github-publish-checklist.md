# GitHub公開チェックリスト（sync-gateway）

公開前にこの順で確認する。

## 1. セキュリティ / 機密

- [ ] `.env` がコミット対象に入っていない
- [ ] APIキー・トークン・Cookie がリポジトリ内に残っていない
- [ ] 実データ（個人レビュー本文など）をサンプルに含めていない
- [ ] `samples/` はダミーデータのみ

## 2. README（公開向け）

- [ ] 何を解決するプロジェクトかを冒頭に1段落で明記
- [ ] アーキテクチャ図（OpenClaw/Relay → gateway → DB/UI）
- [ ] クイックスタート（docker compose）
- [ ] APIキー運用方針（書き込み系のみBearer）
- [ ] 初回同期/差分同期の運用説明
- [ ] スクリーンショット（Overview / Records）

## 3. 設計の肝（見せ場）

- [ ] イベントID設計を明文化
  - 形式: `<source_slug>:<event_key>`
  - 例: `bookmeter:review:133700594`, `filmarks:mark:9876543`
- [ ] 重複防止/更新方針（upsert相当）
- [ ] 欠損許容設計（payload拡張で将来互換）
- [ ] 低速取得 + フォールバック戦略

## 4. 運用実績（可能なら）

- [ ] Bookmeter 同期件数（read/reading/wish）
- [ ] 欠損率サマリ（title/author/event_date）
- [ ] 503等の回避方針（低速・再試行・Relay切替）

## 5. ドキュメント整備

- [ ] `docs/operations-playbook.md`（共通運用）
- [ ] `docs/bookmeter-first-operation.md`
- [ ] `docs/bookmeter-relay-normalization-template.md`
- [ ] `docs/filmarks-first-operation.md`
- [ ] `docs/filmarks-relay-normalization-template.md`
- [ ] （任意）`docs/filmarks-migration-from-bookmeter.md`

## 6. 公開時の見せ方メモ

- APIのないサービスを「個人データ基盤化」する思想を強調
- データ収集手段そのものより、**運用可能性**（安定性・保守性）を推す
- 「初回フル同期 + 以降差分同期」で現実的な運用をアピール

---

必要になったら、このチェックリストをClaude Codeに渡してREADME・docsの最終磨きを依頼する。
