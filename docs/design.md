# arigato-gateway アーキテクチャ設計書

## プロジェクト概要と動機

読書メーター（bookmeter.com）や Filmarks（filmarks.com）などの外部サービスには、公式 API が存在しない、またはアクセスが制限されている。個人の読書・映画鑑賞履歴を自分のデータとして手元に持ちたい、あるいは他のサービスと連携させたいというニーズに対応するため、本プロジェクトを立ち上げた。

`arigato-gateway` は「ありがとうゲートウェイ」の略称でもあり、外部サービスへのスクレイピングを中間層として吸収し、統一された REST API として提供するミドルウェアである。

---

## 技術選定と理由

### Runtime: Bun

Node.js に比べて起動が速く、`bun:sqlite` による SQLite バインディングが標準で内蔵されている。TypeScript をネイティブに実行できるため、ビルドステップが不要であり、開発サイクルが短縮される。

### Framework: Hono

軽量かつ TypeScript フレンドリーな Web フレームワーク。Cloudflare Workers や Bun など複数のランタイムに対応しており、将来的なデプロイ先の変更にも対応しやすい。ルーティングの記述がシンプルで、ミドルウェアの構成も直感的である。

### Scraping: Cheerio

Node.js 版の jQuery とも言える HTML パーサー。ブラウザの DOM API に近い記法でスクレイピングを記述できるため、学習コストが低い。ヘッドレスブラウザ（Puppeteer 等）に比べてオーバーヘッドが小さく、静的な HTML のパースには十分な性能を持つ。

### DB: bun:sqlite (SQLite)

外部サービスへの依存をゼロに抑えるために SQLite を選択した。個人利用・小規模運用を想定しており、PostgreSQL 等の本格的な RDBMS は過剰である。`bun:sqlite` は Bun に内蔵されており、追加インストールが不要で、WAL モードを有効にすることで並行書き込みにも対応できる。

### Admin UI: Alpine.js + Tailwind CDN

管理画面はビルドレスで完結させることを優先した。Alpine.js はスクリプトタグ一つで動作するリアクティブフレームワークであり、単一の HTML ファイルとして配信できる。Tailwind CDN と組み合わせることで、デザインの一貫性を保ちつつ、フロントエンドのビルドパイプラインを完全に排除した。

---

## API 設計方針

REST に準拠したシンプルな設計を採用した。

- `GET /health` — ヘルスチェック。監視システムや Docker のヘルスチェックで利用する。
- `GET /api/scrapers` — スクレイパー一覧
- `POST /api/scrapers/:id/sync` — 手動同期トリガー
- `PUT /api/scrapers/:id` — スクレイパー設定の更新
- `GET /api/booklog/books` — 書籍一覧（検索・ページネーション対応）
- `GET /api/filmarks/movies` — 映画一覧（検索・ページネーション対応）
- `GET /api/jobs` — ジョブ履歴
- `PUT /api/config/scrapers/:id/credentials` — クレデンシャル更新
- `GET /admin/` — 管理ダッシュボード（HTML）

認証は現時点では未実装。ローカルネットワーク内での利用を前提としており、将来的には Bearer トークン認証やネットワーク制限による保護を想定している。

---

## スクレイパープラグインアーキテクチャ

各スクレイパーは `ScraperPlugin` インターフェースを実装したオブジェクトとして定義される。

```typescript
interface ScraperPlugin {
  id: string;
  name: string;
  sync(credentials: Credentials): AsyncGenerator<ScrapeRecord>;
  validate(credentials: Credentials): Promise<boolean>;
}
```

`sync` メソッドは AsyncGenerator を返す。これにより、大量のレコードを一度にメモリに展開することなく、ストリーミング的に処理できる。スケジューラ側は `for await...of` で逐次受け取り、DB に書き込む。

プラグインはレジストリ（`src/scrapers/registry.ts`）に登録される。新しいサービスへの対応は、`ScraperPlugin` を実装したモジュールを追加してレジストリに登録するだけで完結する。

---

## データベーススキーマの設計思想

### scrapers テーブル

スクレイパーの設定情報と最終同期時刻を管理する。クレデンシャルは JSON 文字列として `credentials_json` に格納する。型の柔軟性を持たせることで、サービスごとに異なる認証情報（userId、cookie、API キーなど）に対応できる。

### jobs テーブル

各同期の実行履歴を記録する。`status`（pending / running / completed / failed）、取得件数、エラーメッセージを持ち、管理ダッシュボードでの可視化とデバッグに利用する。

### books / movies テーブル

スクレイピングで取得したデータを正規化して格納する。`raw_json` カラムに元データの全フィールドを保存することで、将来的なスキーマ変更時にも再処理が可能である。`INSERT OR REPLACE` により、再同期時の重複処理を防ぐ。

---

## 管理ダッシュボード設計

ダークテーマを採用し、内部ツールとしての機能性を重視した。

- 左サイドバー: ナビゲーション + ヘルスステータス表示
- ダッシュボードページ: 統計カード、スクレイパー状態、最近のジョブ一覧
- スクレイパーページ: 個別設定、クレデンシャル入力モーダル
- ジョブページ: 全ジョブ履歴の詳細表示
- Books / Movies ページ: 検索フィルター付きデータ一覧

Alpine.js の `x-data` / `x-init` パターンで状態管理を行い、各ページ遷移時に API を再フェッチする。ビルドツールなしの SPA に近い体験を実現している。

---

## 将来の展望

1. **新スクレイパーの追加**: レコチョク、Amazon の購入履歴、Notion データベースへのエクスポートなど、`ScraperPlugin` を実装するだけで容易に拡張できる。
2. **Webhook 通知**: 同期完了時に Discord や Slack への通知を送る仕組みを追加できる。
3. **認証の強化**: CORS + Bearer トークンによる API 認証、または mTLS による保護。
4. **データエクスポート**: CSV / JSON ダウンロードエンドポイントの追加。
5. **Cloudflare Workers への移行**: Hono を使っているため、D1（SQLite 互換）と組み合わせてエッジへのデプロイも視野に入る。
