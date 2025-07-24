# work_logsコレクション設計

## 概要
農業作業記録システムにおける作業ログの管理用コレクション。  
自然言語の作業報告を構造化データとして保存し、検索・分析を可能にする。

## コレクション構造

### 基本情報
- **コレクション名**: `work_logs`
- **データベース**: MongoDB Atlas
- **インデックス戦略**: 検索性能重視の複合インデックス

### スキーマ定義

```javascript
{
  // 基本識別情報
  "_id": ObjectId,                    // MongoDB自動生成ID
  "log_id": "LOG-20250724-A1B2C3D4",  // 人間可読な記録ID
  "user_id": "USER-001",              // 作業者のユーザーID
  
  // 時間情報
  "work_date": ISODate,               // 実際の作業実施日 (重要: created_atと分離)
  "created_at": ISODate,              // 記録作成日時
  "updated_at": ISODate,              // 記録更新日時
  
  // 原文情報
  "original_message": "昨日トマトハウスで防除作業をしました", // ユーザーの元メッセージ
  
  // 構造化された抽出データ
  "extracted_data": {
    // 圃場情報 (ID変換済み)
    "field_id": "FIELD-A01",          // 圃場マスターID
    "field_name": "トマトハウス",       // 正規化済み圃場名
    
    // 作物情報 (ID変換済み)
    "crop_id": "CROP-001",            // 作物マスターID  
    "crop_name": "トマト",             // 正規化済み作物名
    "variety": "桃太郎",               // 品種（オプショナル）
    
    // 資材情報 (ID変換済み配列)
    "material_ids": ["MAT-D001"],     // 資材マスターIDの配列
    "material_names": ["ダコニール1000"], // 正規化済み資材名の配列
    
    // 作業詳細
    "work_details": {
      "dilution_ratio": "1000倍",     // 希釈倍率
      "application_amount": "100L",   // 使用量
      "application_method": "散布",   // 施用方法
      "work_duration": 120,           // 作業時間(分)
      "work_area": 1000,              // 作業面積(㎡)
      "treatment_count": 3            // 防除回数等
    },
    
    // 品質・状況情報
    "quality_info": {
      "work_quality": "良好",         // 作業品質
      "crop_condition": "健全",       // 作物状態
      "weather_condition": "曇り",    // 天候
      "temperature": 25,              // 気温(℃)
      "humidity": 65,                 // 湿度(%)
      "notes": "病斑は見られず"       // 補足メモ
    }
  },
  
  // 分類・タグ情報
  "category": "防除",                 // 作業分類 (防除/施肥/栽培/収穫/管理/その他)
  "subcategory": "殺菌剤散布",        // 詳細分類
  "tags": ["防除", "殺菌剤", "予防"],  // 検索用タグ配列
  
  // メタデータ
  "confidence": 0.85,                 // 情報抽出の信頼度 (0.0-1.0)
  "extraction_method": "auto",        // 抽出方法 (auto/manual/hybrid)
  "status": "confirmed",              // 記録状態 (draft/confirmed/reviewed)
  "review_status": {
    "is_reviewed": false,             // レビュー完了フラグ
    "reviewed_by": null,              // レビュー者ID
    "reviewed_at": null,              // レビュー日時
    "review_notes": null              // レビューコメント
  },
  
  // 関連情報
  "related_task_id": "TASK-002",      // 関連タスクID（オプショナル）
  "photo_urls": [],                   // 作業写真URL配列
  "attachments": [],                  // 添付ファイル情報
  
  // システム情報
  "source": "line_bot",               // データソース (line_bot/web_ui/api)
  "version": "1.0",                   // スキーマバージョン
  "sync_status": {
    "last_synced": ISODate,           // 最終同期日時
    "sync_errors": []                 // 同期エラー記録
  }
}
```

## インデックス設計

### 1. 主要検索インデックス
```javascript
// 複合インデックス: ユーザー + 作業日 + 分類
db.work_logs.createIndex({
  "user_id": 1,
  "work_date": -1,
  "category": 1
}, {
  name: "idx_user_workdate_category"
})

// 圃場別検索インデックス
db.work_logs.createIndex({
  "user_id": 1,
  "extracted_data.field_id": 1,
  "work_date": -1
}, {
  name: "idx_user_field_workdate"
})

// 資材検索インデックス
db.work_logs.createIndex({
  "user_id": 1,
  "extracted_data.material_ids": 1,
  "work_date": -1
}, {
  name: "idx_user_materials_workdate"
})
```

### 2. 全文検索インデックス
```javascript
// 原文メッセージの全文検索
db.work_logs.createIndex({
  "original_message": "text",
  "extracted_data.field_name": "text",
  "extracted_data.crop_name": "text",
  "extracted_data.material_names": "text"
}, {
  name: "idx_fulltext_search"
})
```

### 3. 分析用インデックス
```javascript
// 統計分析用
db.work_logs.createIndex({
  "category": 1,
  "work_date": -1,
  "user_id": 1
}, {
  name: "idx_analytics_category"
})

// 信頼度フィルタ用
db.work_logs.createIndex({
  "confidence": -1,
  "status": 1
}, {
  name: "idx_quality_filter"
})
```

## データ運用方針

### 1. データ品質管理
- **信頼度スコア**: 0.7未満は要レビュー対象
- **ステータス管理**: draft → confirmed → reviewed
- **自動検証**: 日付の妥当性、必須項目の存在確認

### 2. データ保持戦略
- **アクティブデータ**: 直近2年分
- **アーカイブデータ**: 2年以上経過分は別コレクションに移動
- **バックアップ**: 日次自動バックアップ

### 3. プライバシー・セキュリティ
- **個人情報**: user_idによる間接参照
- **アクセス制御**: ユーザー別データ分離
- **監査ログ**: 重要操作の記録

## 使用例

### 登録処理例
```javascript
// 作業記録の登録
await db.work_logs.insertOne({
  log_id: "LOG-20250724-A1B2C3D4",
  user_id: "USER-001",
  work_date: new Date("2025-07-23"),
  original_message: "昨日トマトハウスで防除作業をしました",
  extracted_data: {
    field_id: "FIELD-A01",
    field_name: "トマトハウス",
    crop_id: "CROP-001", 
    crop_name: "トマト",
    material_ids: ["MAT-D001"],
    material_names: ["ダコニール1000"]
  },
  category: "防除",
  tags: ["防除", "殺菌剤"],
  confidence: 0.85,
  status: "confirmed",
  created_at: new Date(),
  updated_at: new Date()
})
```

### 検索処理例
```javascript
// 期間別検索
await db.work_logs.find({
  user_id: "USER-001",
  work_date: {
    $gte: new Date("2025-07-01"),
    $lte: new Date("2025-07-31")
  },
  category: "防除"
}).sort({ work_date: -1 })

// 圃場別作業履歴
await db.work_logs.find({
  "user_id": "USER-001",
  "extracted_data.field_id": "FIELD-A01"
}).sort({ work_date: -1 })

// 資材使用統計
await db.work_logs.aggregate([
  {
    $match: {
      user_id: "USER-001",
      "extracted_data.material_ids": { $exists: true }
    }
  },
  {
    $unwind: "$extracted_data.material_ids"
  },
  {
    $group: {
      _id: "$extracted_data.material_ids",
      count: { $sum: 1 },
      latest_use: { $max: "$work_date" }
    }
  }
])
```

## 注意事項

1. **work_dateとcreated_atの分離**: 実際の作業日と記録日は別管理
2. **ID正規化**: 全ての外部参照はマスターデータのIDで管理
3. **配列フィールド**: material_idsやtagsは配列で複数値対応
4. **信頼度管理**: 自動抽出の品質を数値で管理
5. **拡張性**: 新しい作業種別や情報項目の追加に対応

このスキーマにより、農業作業記録の効率的な管理と高度な分析が可能になります。