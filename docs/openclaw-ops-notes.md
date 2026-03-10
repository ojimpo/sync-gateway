# OpenClaw運用メモ（実運用上の注意）

このメモは、**OpenClawエージェント運用で事故りやすい点**を先回りでまとめたもの。

## 1. このサービスの責務を守る

arigato-gateway は「スクレイピング実行機」ではなく、以下に責務を限定する。

- 受け口 API（ingest）
- source/run/records の保存
- 管理UIでの可視化

スクレイピング本体（ログイン操作、ページ遷移、抽出）は OpenClaw Browser Relay 側で実施する。

---

## 2. Browser Relay 前提の実務フロー（推奨）

### OpenClaw即応テンプレ（毎回使う）

- health確認: `GET /healthz`
- source確認: `GET /api/v1/sources`
- 未登録なら登録: `POST /api/v1/sources/register`
- 正規化して投入: `POST /api/v1/ingest/events`
- 反映確認: `GET /api/v1/records?limit=20`


1. Browser Relay で対象サイトにアクセス
2. 必要データを抽出（タイトル、著者/監督、評価、日時、URLなど）
3. 正規化JSONを作成
4. `POST /api/v1/ingest/events` で投入
5. `GET /api/v1/records` と管理UIで反映確認

### 重要
- **抽出前のHTML依存を最小化**（UI変更に弱い）
- 「取れなかった項目」は null で送る（欠損許容）
- 1件失敗で全件落とさない（バッチ内部分失敗許容）

---

## 3. Source登録の扱い

- 初回のみ `POST /api/v1/sources/register`
- 以降は既存sourceへ投入
- slug命名は固定運用（例: `bookmeter`, `filmarks`）

slugを途中で変えると分析側・連携側が壊れやすい。変更するなら移行手順を明示すること。

---

## 4. 個人情報・機密情報の扱い

- リポジトリにはCookie/Tokenを置かない
- Browser Relay上のログインは運用時に都度行う
- payloadには必要最小限のみ投入（本文全量や不要なプロフィール情報は持ち込まない）

---

## 5. 失敗時の切り分け順

1. `GET /healthz` が生きているか
2. sourceが登録済みか
3. ingest payload の型崩れがないか
4. records へ保存されているか
5. UIはAPIを参照できているか（CORS/プロキシ/ポート）

---

## 6. 将来拡張の推奨

- source追加は「抽出ロジック追加 + 既存ingest API再利用」で対応
- run管理（`/api/v1/runs`）を積極活用して、ジョブ単位で成功/失敗を残す
- 必要になった段階で認証・監査ログを追加（内部限定運用のままなら後回し可）

---

## 7. health-ojimpo 連携メモ

最終的には health-ojimpo 側が以下を定期実行できればよい。

- arigato-gateway から `records` を取得
- ソース別に集計
- 既存スコアリングへ取り込み

中間APIを挟んだことで、スクレイピング方式を変更しても health-ojimpo の取り込み契約は維持しやすい。
