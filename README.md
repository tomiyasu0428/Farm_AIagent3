# 農業管理AIエージェント

LINE Bot を通じて農業作業を支援するAIエージェントシステム

## 概要

このシステムは、農業従事者がLINEで簡単に農作業の相談ができるAIエージェントです。MongoDB に蓄積された農業データを基に、LangChain を使用して最適な作業指示や農薬の選定を行います。

## 主な機能

- **タスク管理**: 今日のタスクや作業予定の確認
- **圃場情報**: 圃場の現在の状況や作付け情報の取得
- **農薬指導**: 適切な農薬の選定と希釈倍率の提案
- **作業記録**: 作業完了の報告と自動スケジューリング
- **在庫管理**: 資材の在庫状況確認

## 技術スタック

- **Python 3.9+**
- **LangChain**: AIエージェント フレームワーク
- **MongoDB**: データベース
- **FastAPI**: Web APIフレームワーク  
- **LINE Bot SDK**: LINE連携
- **OpenAI GPT-4**: 大規模言語モデル

## セットアップ

### 1. 仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example` を `.env` にコピーして、以下の値を設定してください：

```env
OPENAI_API_KEY=your_openai_api_key_here
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/agri_ai
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here
LINE_CHANNEL_SECRET=your_line_channel_secret_here
```

### 4. データベースの準備

MongoDB Atlas でデータベースを作成し、`docs/MongoDBデータベース設計.md` に従ってコレクションを設定してください。

## 起動方法

### 開発環境での起動

```bash
python run_server.py
```

サーバーは http://localhost:8000 で起動します。

### ヘルスチェック

```bash
curl http://localhost:8000/health
```

## LINE Bot の設定

1. LINE Developers Console でBot を作成
2. Webhook URL を `https://your-domain.com/webhook` に設定
3. 必要な権限を付与

## プロジェクト構造

```
src/agri_ai/
├── core/                    # コア機能
│   ├── __init__.py
│   ├── config.py           # 設定管理
│   └── agent.py            # LangChain エージェント
├── database/               # データベース関連
│   ├── __init__.py
│   ├── mongodb_client.py   # MongoDB 接続
│   └── models.py           # データモデル
├── langchain_tools/        # LangChain ツール
│   ├── __init__.py
│   ├── base_tool.py        # 基底ツール
│   ├── task_lookup_tool.py # タスク検索
│   └── field_info_tool.py  # 圃場情報取得
├── line_bot/               # LINE Bot関連
│   ├── __init__.py
│   └── webhook.py          # Webhook処理
└── utils/                  # ユーティリティ
    └── __init__.py
```

## 開発フェーズ

### Phase 0 - 基盤構築 ✅
- [x] 環境セットアップ
- [x] MongoDB接続実装
- [x] LangChain エージェント基盤
- [x] LINE Webhook実装

### Phase 1 - 基本機能
- [ ] タスク管理機能の完成
- [ ] 圃場情報取得機能の完成
- [ ] 農薬提案機能の実装
- [ ] 作業記録機能の実装

### Phase 2 - 管理機能
- [ ] Web ダッシュボードの実装
- [ ] マスターデータ管理
- [ ] ユーザー管理機能

## テスト

```bash
# 単体テスト実行
pytest tests/unit/

# 統合テスト実行
pytest tests/integration/

# 全テスト実行
pytest
```

## ログ

アプリケーションログは `agri_ai.log` に出力されます。

## 貢献

開発に参加される場合は、以下のガイドラインに従ってください：

1. 全てのコメントとドキュメントは日本語で記述
2. コードはPEP 8に準拠
3. 新機能には必ずテストを追加
4. セキュリティに関する情報は適切に管理

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## サポート

問題やバグを発見した場合は、GitHubのIssuesに報告してください。