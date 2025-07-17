# LangSmith 統合設定ガイド

このガイドでは、農業AIエージェントにLangSmithのトレーシング機能を統合する手順を説明します。

## LangSmithとは

LangSmithは、LangChainアプリケーションの観測性、テスト、評価のためのプラットフォームです。エージェントの動作を詳細にトレース・監視することができます。

## 設定手順

### 1. LangSmithアカウントの作成

1. [LangSmith](https://smith.langchain.com/)にアクセス
2. アカウントを作成・ログイン
3. 新しいプロジェクトを作成（例：`agri-ai-project`）

### 2. APIキーの取得

1. LangSmithダッシュボードで設定ページに移動
2. API Keysセクションで新しいAPIキーを作成
3. APIキーをコピー（後で使用）

### 3. 環境変数の設定

`.env`ファイルに以下の設定を追加：

```env
# LangSmith設定
LANGSMITH_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxx  # 取得したAPIキー
LANGSMITH_PROJECT=agri-ai-project                # プロジェクト名
LANGSMITH_TRACING=true                           # トレーシングを有効化
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

### 4. 設定の確認

設定が正しく行われているかテストスクリプトで確認：

```bash
python test_langsmith_integration.py
```

正常に設定されている場合、以下のようなメッセージが表示されます：

```
=== 環境変数の確認 ===
LANGSMITH_API_KEY: 設定済み
LANGSMITH_PROJECT: agri-ai-project
LANGSMITH_TRACING: True
LANGSMITH_ENDPOINT: https://api.smith.langchain.com

=== LangChain環境変数 ===
LANGCHAIN_TRACING_V2: true
LANGCHAIN_API_KEY: 設定済み
LANGCHAIN_PROJECT: agri-ai-project
LANGCHAIN_ENDPOINT: https://api.smith.langchain.com
```

## トレーシング機能の確認

### LINE Botでのトレーシング

設定が完了したら、LINE Botを起動してメッセージを送信：

```bash
python run_server.py
```

LINEでメッセージを送信すると、LangSmithダッシュボードで以下の情報が確認できます：

- エージェントの実行フロー
- 各ツールの実行時間
- LLMへのプロンプトと応答
- エラーやデバッグ情報

### ダッシュボードでの確認

1. [LangSmith](https://smith.langchain.com/)にログイン
2. プロジェクト（`agri-ai-project`）を選択
3. **Traces**タブで実行ログを確認
4. 個別のトレースをクリックして詳細を表示

## 監視できる情報

LangSmithでは以下の情報を詳細に監視できます：

### エージェント実行フロー
- 各ツールの実行順序
- 実行時間と待機時間
- 成功・失敗の状況

### LLM相互作用
- プロンプトの内容
- LLMの応答
- トークン使用量
- レスポンス時間

### ツール実行
- 各ツール（TaskLookupTool、FieldInfoToolなど）の実行結果
- データベースクエリ
- エラー情報

### パフォーマンス分析
- 実行時間の分析
- ボトルネックの特定
- 使用量統計

## トラブルシューティング

### トレーシングが表示されない場合

1. **APIキーの確認**
   ```bash
   echo $LANGSMITH_API_KEY
   ```

2. **環境変数の確認**
   ```bash
   python test_langsmith_integration.py
   ```

3. **ネットワーク接続の確認**
   - ファイアウォールの設定を確認
   - プロキシ設定がある場合は適切に設定

### エラーメッセージの対処

- `Authentication failed`: APIキーが正しくない
- `Project not found`: プロジェクト名が間違っている
- `Connection timeout`: ネットワーク接続の問題

## 参考リンク

- [LangSmith公式ドキュメント](https://docs.smith.langchain.com/)
- [LangChain トレーシングガイド](https://python.langchain.com/docs/langsmith/walkthrough)
- [LangSmith Python SDK](https://github.com/langchain-ai/langsmith-sdk)

## まとめ

LangSmithの統合により、以下のメリットが得られます：

✅ **可視性の向上**: エージェントの動作を詳細に把握  
✅ **デバッグの効率化**: エラー原因の特定が容易  
✅ **パフォーマンス最適化**: ボトルネックの発見と改善  
✅ **監査ログ**: 全ての実行履歴を記録  
✅ **チーム共有**: 複数メンバーでの監視・分析 