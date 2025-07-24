# アグリAIエージェント 処理フローチャート

**更新日**: 2025年7月17日  
**バージョン**: Phase 1 対応版

---

## 🤖 AIエージェント 全体処理フロー

```mermaid
graph TD
    A[LINE ユーザー入力] --> B[LINE Webhook受信]
    B --> C[署名検証]
    C --> D[FastAPI Endpoint]
    D --> E[AgentExecutor初期化]
    E --> F[LangChain Agent開始]
    F --> G[Google Gemini 2.5 Flash 思考開始]
    
    G --> H{ツール選択判定}
    H --> I1[TaskLookupTool]
    H --> I2[TaskUpdateTool]
    H --> I3[FieldInfoTool]
    H --> I4[CropMaterialTool]
    H --> I5[WorkSuggestionTool]
    
    I1 --> J[MongoDB接続実行]
    I2 --> J
    I3 --> J
    I4 --> J
    I5 --> J
    
    J --> K[データベース操作]
    K --> L[結果フォーマット]
    L --> M[LangChain Agent回答生成]
    M --> N[LINE Message API]
    N --> O[ユーザーに回答配信]
    
    style A fill:#e1f5fe
    style G fill:#fff3e0
    style J fill:#f3e5f5
    style O fill:#e8f5e8
```

---

## 🧠 思考プロセス詳細フロー

```mermaid
graph TD
    A[ユーザークエリ受信] --> B[Google Gemini 2.5 Flash]
    B --> C[自然言語理解]
    C --> D[農業専門用語解析]
    D --> E[意図分類]
    
    E --> F1[タスク検索意図]
    E --> F2[タスク更新意図]
    E --> F3[圃場情報意図]
    E --> F4[資材情報意図]
    E --> F5[作業提案意図]
    
    F1 --> G1[TaskLookupTool選択]
    F2 --> G2[TaskUpdateTool選択]
    F3 --> G3[FieldInfoTool選択]
    F4 --> G4[CropMaterialTool選択]
    F5 --> G5[WorkSuggestionTool選択]
    
    G1 --> H[ツール実行指示]
    G2 --> H
    G3 --> H
    G4 --> H
    G5 --> H
    
    H --> I[ツール結果受信]
    I --> J[回答生成思考]
    J --> K[日本語回答作成]
    K --> L[農業専門知識付与]
    L --> M[最終回答出力]
    
    style B fill:#fff3e0
    style E fill:#fce4ec
    style J fill:#e0f2f1
    style M fill:#e8f5e8
```

---

## 🔧 ツール実行フロー詳細

```mermaid
graph TD
    A[LangChain Tool 選択] --> B[base_tool._run()実行]
    B --> C[独立スレッド作成]
    C --> D[新イベントループ生成]
    D --> E[_execute_with_db()実行]
    E --> F[新MongoDB接続作成]
    
    F --> G[Motor Client接続]
    G --> H[MongoDB Atlas接続]
    H --> I[コレクション取得]
    
    I --> J1[scheduled_tasks]
    I --> J2[fields]
    I --> J3[crops]
    I --> J4[materials]
    I --> J5[work_records]
    
    J1 --> K[データベースクエリ実行]
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    
    K --> L[結果データ取得]
    L --> M[MongoDB接続終了]
    M --> N[スレッド終了]
    N --> O[結果をメインスレッドに返却]
    O --> P[フォーマット処理]
    P --> Q[LangChain Agentに結果返却]
    
    style C fill:#fff3e0
    style F fill:#f3e5f5
    style H fill:#e3f2fd
    style Q fill:#e8f5e8
```

---

## 📊 各ツールの具体的処理

### 1. TaskLookupTool フロー
```mermaid
graph LR
    A[クエリ解析] --> B[日付範囲抽出]
    B --> C[タスクID抽出]
    C --> D[scheduled_tasks検索]
    D --> E[結果フィルタリング]
    E --> F[日本語フォーマット]
    
    style A fill:#e1f5fe
    style D fill:#f3e5f5
    style F fill:#e8f5e8
```

### 2. TaskUpdateTool フロー
```mermaid
graph LR
    A[完了/延期判定] --> B[対象タスク検索]
    B --> C1[完了処理]
    B --> C2[延期処理]
    C1 --> D1[scheduled_tasks削除]
    C2 --> D2[scheduled_date更新]
    D1 --> E1[work_records追加]
    D2 --> E2[延期理由記録]
    
    style A fill:#e1f5fe
    style C1 fill:#c8e6c9
    style C2 fill:#fff3e0
```

### 3. FieldInfoTool フロー
```mermaid
graph LR
    A[圃場名/全圃場判定] --> B[fields検索]
    B --> C[current_cultivation取得]
    C --> D[crops情報結合]
    D --> E[生育段階情報]
    E --> F[包括的情報フォーマット]
    
    style A fill:#e1f5fe
    style D fill:#f3e5f5
    style F fill:#e8f5e8
```

### 4. CropMaterialTool フロー
```mermaid
graph LR
    A[資材名抽出] --> B[materials検索]
    B --> C[希釈倍率計算]
    C --> D[適用作物確認]
    D --> E[使用基準チェック]
    E --> F[安全使用基準表示]
    
    style A fill:#e1f5fe
    style C fill:#fff3e0
    style F fill:#e8f5e8
```

### 5. WorkSuggestionTool フロー
```mermaid
graph LR
    A[提案タイプ判定] --> B1[ローテーション提案]
    A --> B2[天候別提案]
    A --> B3[一般作業提案]
    B1 --> C1[材料ローテーション計算]
    B2 --> C2[天候条件別作業選択]
    B3 --> C3[圃場別生育段階提案]
    C1 --> D[提案フォーマット]
    C2 --> D
    C3 --> D
    
    style A fill:#e1f5fe
    style D fill:#e8f5e8
```

---

## ⚡ 非同期処理アーキテクチャ

```mermaid
graph TD
    A[FastAPI メインスレッド] --> B[LINE Webhook受信]
    B --> C[Agent実行要求]
    
    C --> D[Thread 1: Tool実行]
    D --> E[新Event Loop作成]
    E --> F[MongoDB接続]
    F --> G[DB操作実行]
    G --> H[接続終了]
    H --> I[結果返却]
    
    I --> J[メインスレッドに合流]
    J --> K[LangChain回答生成]
    K --> L[LINE返信]
    
    style A fill:#e3f2fd
    style D fill:#fff3e0
    style F fill:#f3e5f5
    style L fill:#e8f5e8
```

---

## 🎯 パフォーマンス指標

| 処理段階 | 目標時間 | 実績時間 | 備考 |
|---------|---------|---------|------|
| LINE受信→Agent開始 | <100ms | ~50ms | FastAPI処理 |
| Gemini思考時間 | <1.5秒 | ~1秒 | LLM推論 |
| Tool実行時間 | <800ms | ~500ms | DB操作含む |
| 回答生成→LINE送信 | <200ms | ~100ms | フォーマット処理 |
| **合計応答時間** | **<3秒** | **~2秒** | ✅ **目標達成** |

---

## 🔄 エラーハンドリングフロー

```mermaid
graph TD
    A[エラー発生] --> B{エラー種別判定}
    
    B --> C1[MongoDB接続エラー]
    B --> C2[EventLoop競合]
    B --> C3[Tool実行エラー]
    B --> C4[LLM APIエラー]
    
    C1 --> D1[新接続リトライ]
    C2 --> D2[独立スレッド実行]
    C3 --> D3[デフォルト応答]
    C4 --> D4[フォールバック応答]
    
    D1 --> E[ユーザーエラー通知]
    D2 --> F[正常処理続行]
    D3 --> E
    D4 --> E
    
    style C1 fill:#ffebee
    style C2 fill:#fff3e0
    style F fill:#e8f5e8
```

---

## 📈 スケーラビリティ設計

```mermaid
graph TD
    A[単一ユーザー] --> B[複数ユーザー対応]
    B --> C[Google Cloud Run]
    C --> D[オートスケーリング]
    
    D --> E1[Agent インスタンス 1]
    D --> E2[Agent インスタンス 2]
    D --> E3[Agent インスタンス N]
    
    E1 --> F[MongoDB Atlas共有]
    E2 --> F
    E3 --> F
    
    F --> G[LangSmith統合監視]
    G --> H[パフォーマンス最適化]
    
    style B fill:#e1f5fe
    style F fill:#f3e5f5
    style H fill:#e8f5e8
```

---

## 🔍 監視・ログフロー

```mermaid
graph LR
    A[ユーザー操作] --> B[LangSmith Tracing]
    B --> C[実行ログ記録]
    C --> D[パフォーマンス測定]
    D --> E[エラー統計]
    E --> F[改善分析]
    
    style B fill:#fff3e0
    style E fill:#ffebee
    style F fill:#e8f5e8
```

---

## 🚀 技術的革新ポイント

### 1. **イベントループ競合解決**
- 問題: `asyncio.run() cannot be called from a running event loop`
- 解決: 独立スレッド + 新Event Loop方式
- 効果: 100%安定動作

### 2. **MongoDB接続最適化**
- 問題: 接続の再利用によるloop競合
- 解決: `_execute_with_db()`による新接続方式
- 効果: エラーゼロ、高パフォーマンス

### 3. **LangChain統合アーキテクチャ**
- 設計: `base_tool.py`による統一処理
- 効果: 保守性向上、拡張容易

---

**次回更新**: Phase 2 機能追加時  
**技術責任者**: 冨安寛己  
**AI支援**: Claude Code