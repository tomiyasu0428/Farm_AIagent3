# 農業管理AIエージェント

LINE Bot を通じて農業作業を支援するAIエージェントシステム

## 概要

このシステムは、農業従事者がLINEで簡単に農作業の相談ができるAIエージェントです。MongoDB に蓄積された農業データを基に、LangChain を使用して最適な作業指示や農薬の選定を行います。

## 主な機能

- **圃場情報管理**: 圃場の登録、更新、および圃場に関する情報の取得
- **作業記録登録**: LINEを通じて日々の農作業内容を自然言語で記録・管理
- **AIエージェントによる対話**: ユーザーの質問や指示に基づき、適切な情報提供やタスク実行を支援

## 作業記録の登録方法

作業記録の登録方法については、[こちら](docs/作業記録の管理方法.md) を参照してください。

## 技術スタック

- **Python 3.9+**
- **LangChain**: AIエージェント フレームワーク
- **MongoDB**: データベース
- **FastAPI**: Web APIフレームワーク  
- **LINE Bot SDK**: LINE連携
- **Google Gemini 2.5 Flash**: 大規模言語モデル

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
GOOGLE_API_KEY=your_google_api_key_here
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
├── agents/                  # 各種専門エージェント
│   ├── field_agent.py
│   ├── work_log_registration_agent.py
│   └── work_log_search_agent.py
├── core/                    # コア機能
│   ├── config.py           # 設定管理
│   ├── master_agent.py     # 司令塔エージェント
│   └── error_handler.py    # エラーハンドリング
├── database/               # データベース関連
│   ├── data_access.py      # データアクセス層
│   ├── models.py           # データモデル
│   └── mongodb_client.py   # MongoDB クライアント
├── langchain_tools/        # LangChain ツール
│   ├── base_tool.py        # 基底ツール
│   ├── field_agent_tool.py
│   └── work_log_registration_agent_tool.py
├── line_bot/               # LINE Bot関連
│   └── webhook.py          # Webhook処理
├── services/               # サービス層
│   ├── field_name_extractor.py
│   ├── master_data_resolver.py
│   └── query_analyzer.py
└── utils/                  # ユーティリティ
    └── query_parser.py
```

## 開発フェーズ

### Phase 0 - 基盤構築 ✅
- [x] 環境セットアップ
- [x] MongoDB接続実装
- [x] LangChain エージェント基盤
- [x] LINE Webhook実装

### Phase 1 - マルチエージェント・アーキテクチャと作業記録機能 ✅
- [x] マルチエージェント・アーキテクチャへのリファクタリング
- [x] 作業記録登録機能の基盤構築

### Phase 2 - 作業記録検索と会話履歴
- [ ] 作業記録検索機能の実装
- [ ] ユーザーとの会話履歴を記憶する機能の追加

### Phase 3 - 管理機能とテスト
- [ ] Web ダッシュボードの実装
- [ ] マスターデータ管理
- [ ] ユーザー管理機能
- [ ] 各機能の単体テストおよび結合テストの実施

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