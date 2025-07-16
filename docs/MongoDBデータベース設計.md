# 農業管理AIエージェント ─ MongoDB データベース設計書

作成日: 2025-07-16
作成者: 冨安 / AI 支援

---
## 1. 目的
Airtable 運用中の「圃場管理・作付け計画・タスク管理」データを MongoDB へ移行し、LangChain + LINE エージェントが高速に参照・更新できる基盤を構築する。

---
## 2. コレクション一覧
| コレクション | 役割 | 主キー | 参照関係 | 備考 |
|--------------|------|--------|----------|------|
| crops | 作物マスター | `_id(ObjectId)` | materials(配列参照) | 栽培カレンダー/病害虫リスク含む |
| materials | 資材マスター | `_id` | – | 農薬/肥料共通 |
| fields | 圃場マスター | `_id(ObjectId)` | crops (embedded) | 現在作付け・次回作業を保持 |
| cultivation_plans | 作付け計画 | `_id` | fields.field_id | 1圃場×1年ドキュメント |
| work_records | 作業履歴(完了) | `_id` | field_id, material_id | 時系列実績データ |
| auto_tasks | 未来タスク(未実施) | `_id` | field_id | 日次バッチ/LINE 通知用 |
| workers | 作業者マスター | `_id` | – | LINEアカウント紐付け |
| sensor_logs | センサーデータ | `_id` | field_id | 圃場環境ログ |
| weather_forecasts | 気象予報 | `_id` | – | 外部API取り込み |
| inventory | 資材在庫 | `_id` | material_id | しきい値監視 |
| purchase_orders | 資材発注 | `_id` | material_id | 発注・受領管理 |
| notifications | 通知設定 | `_id` | owner_id | LINE/メール等 |
| schedule_rules | 自動スケジュール規則 | `_id` | owner_id | 作業生成ルール |

---
## 3. ドキュメント定義

### 3.1 crops
```jsonc
{
  "_id": ObjectId,
  "name": "トマト",
  "variety": "桃太郎",
  "category": "果菜類",
  "cultivation_calendar": [
    { "stage": "育苗期", "days_from_planting": [0,30], "key_activities": ["灌水","温度管理"] }
  ],
  "disease_pest_risks": [
    { "name": "疫病", "risk_period": ["5月","6月"], "prevention_materials": ["銅水和剤"] }
  ],
  "applicable_materials": [
    { "material_id": ObjectId, "application_timing": "生育期", "dilution_rate": "1000倍" }
  ]
}
```

### 3.2 materials
```jsonc
{
  "_id": ObjectId,
  "name": "ダコニール1000",
  "type": "殺菌剤",
  "active_ingredient": "TPN",
  "dilution_rates": { "tomato": "1000倍" },
  "preharvest_interval": 7,
  "max_applications_per_season": 5,
  "rotation_group": "M",
  "target_diseases": ["疫病"],
  "usage_restrictions": { "bee_toxicity": "注意" }
}
```

### 3.3 fields
```jsonc
{
  "_id": ObjectId,
  "field_code": "F01",
  "name": "橋向こう①",
  "area": 1.2,
  "location": { "lat": 35.12, "lon": 139.56 },
  "soil_type": "砂壌土",
  "current_cultivation": {
    "crop_id": ObjectId,
    "variety": "桃太郎",
    "planting_date": "2024-03-15",
    "growth_stage": "開花期"
  },
  "next_scheduled_work": {
    "work_type": "防除",
    "scheduled_date": "2024-07-17",
    "materials": [ObjectId]
  }
}
```

### 3.4 cultivation_plans
```jsonc
{
  "_id": ObjectId,
  "year": 2025,
  "field_id": ObjectId,
  "crop_rotations": [
    {
      "season": "春作",
      "crop_id": ObjectId,
      "variety": "SK9-099",
      "sowing_plan": "2025-04-14",
      "sowing_actual": "2025-04-12",
      "transplant_plan": "2025-05-24",
      "transplant_actual": "2025-05-24",
      "harvest_window": ["2025-07-01","2025-07-31"],
      "estimated_yield": 1320
    }
  ],
  "annual_target_yield": 2400,
  "resource_allocation": { "labor_hours": 480, "material_budget": 150000 }
}
```

### 3.5 work_records
```jsonc
{
  "_id": ObjectId,
  "field_id": ObjectId,
  "work_date": "2025-05-24",
  "work_type": "定植",
  "worker": "田中太郎",
  "materials_used": [],
  "work_details": { "start_time": "08:00", "end_time": "09:30", "notes": "苗の活着良好" },
  "next_work_scheduled": { "work_type": "防除", "scheduled_date": "2025-05-31", "auto_generated": true },
  "created_at": ISODate("2025-05-24T09:30:00Z")
}
```

### 3.6 auto_tasks（省略：work_records と同じ構造で `status: "pending"` を持つ）

### 3.7 workers
```jsonc
{
  "_id": ObjectId,
  "name": "佐藤花子",
  "role": "worker",        // admin / manager / worker
  "line_user_id": "Uxxxxxxxx",
  "skills": ["摘芯", "トラクタ運転"],
  "is_active": true,
  "created_at": ISODate("2025-07-16T00:00:00Z")
}
```

### 3.8 sensor_logs
```jsonc
{
  "_id": ObjectId,
  "field_id": ObjectId,
  "sensor_type": "soil_moisture",   // air_temp / humidity / EC etc.
  "value": 23.4,
  "unit": "%",
  "logged_at": ISODate("2025-07-16T05:00:00Z")
}
```

### 3.9 weather_forecasts (外部API取り込み用)
```jsonc
{
  "_id": ObjectId,
  "grid_point": {
    "lat": 35.12,
    "lon": 139.56
  },
  "forecast_time": ISODate("2025-07-16T06:00:00Z"),
  "weather": {
    "temp": 30,
    "humidity": 70,
    "rain_probability": 60
  }
}
```

### 3.10 inventory
```jsonc
{
  "_id": ObjectId,
  "material_id": ObjectId,
  "current_qty": 12.5,
  "unit": "L",
  "min_threshold": 10,
  "updated_at": ISODate("2025-07-15T15:00:00Z")
}
```

### 3.11 purchase_orders
```jsonc
{
  "_id": ObjectId,
  "order_no": "PO-202507-001",
  "material_id": ObjectId,
  "quantity": 20,
  "unit": "L",
  "status": "ordered",   // ordered / received / canceled
  "ordered_at": ISODate("2025-07-16"),
  "received_at": null
}
```

### 3.12 notifications (ユーザー通知設定)
```jsonc
{
  "_id": ObjectId,
  "owner_id": ObjectId,
  "type": "daily_task_push",
  "send_time": "07:00",
  "channel": "LINE"
}
```

### 3.13 schedule_rules
```jsonc
{
  "_id": ObjectId,
  "rule_name": "防除インターバル",
  "work_type": "防除",
  "interval_days": 7,
  "is_active": true,
  "created_at": ISODate("2025-07-16")
}
```

---
## 4. インデックス設計
| コレクション | フィールド | 目的 |
|--------------|-----------|------|
| fields | `field_code` (unique) | 圃場検索 |
| fields | `next_scheduled_work.scheduled_date` | 直近タスク抽出 |
| work_records | `field_id, work_date` (compound) | 圃場×日付の履歴検索 |
| work_records | `work_type, work_date` | 作業種別統計 |
| materials | `name` (text) | 資材検索 |
| crops | `name`, `category` | 作物検索 |
| workers | `name`, `line_user_id` | 作業員検索・LINE連携 |
| sensor_logs | `field_id, logged_at` | 圃場×時系列センサ検索 |
| inventory | `material_id` | 在庫照会 |
| weather_forecasts | `grid_point.lat, grid_point.lon, forecast_time` | 位置×時間クエリ |
| notifications | `owner_id, type` | 通知設定検索 |
| schedule_rules | `owner_id, work_type` | 自動タスク生成 |

---
## 5. データ移行フロー
1. **Airtable エクスポート**: 3 テーブルを CSV 出力
2. **ETL スクリプト (Python)**
   - 行データ → 上記ドキュメントへ変形
   - 外部キー列を ObjectId 生成に置換
3. **mongoimport** で投入
4. **Index 作成** (`db.work_records.createIndex({...})`)
5. **LangChain エージェント テスト**
   - `fields` → 圃場情報取得
   - `work_records` → 今日のタスク生成
6. LINE 連携でレスポンスタイム <3 秒を確認

---
## 6. 今後の拡張予定
- **センサーデータ連携**: `sensor_logs` コレクション追加
- **画像診断結果**: `image_diagnosis` コレクション追加予定
- **ユーザーアクセスログ**: `user_logs` で問い合わせ内容を蓄積し AI 学習に活用

---
## 7. ゼロスタート運用時の留意点（ユーザーが最初から入力する場合）

1. **参照整合性を UI で担保**
   - `current_cultivation.crop_id` や `materials_used.material_id` など ObjectId 参照は、フォームのプルダウン／オートコンプリートで選択させる。
   - バックエンドでスキーマバリデーションを行い、存在しない ID が渡された場合 4xx を返す。

2. **必須・任意フィールドの明確化**
   | コレクション | 必須フィールド | 任意フィールド |
   |--------------|---------------|---------------|
   | crops | `name`, `category` | `variety`, `disease_pest_risks`, … |
   | materials | `name`, `type` | `dilution_rates`, `usage_restrictions` |
   | fields | `field_code`, `name`, `area` | `soil_type`, `location` |
   | cultivation_plans | `year`, `field_id`, `crop_rotations` | `resource_allocation` |
   | work_records | `field_id`, `work_date`, `work_type` | `materials_used`, `next_work_scheduled` |
   | auto_tasks | `field_id`, `scheduled_date`, `work_type` | `priority`, `notes` |

3. **初期データ投入シーケンス**
   1. 最小限の **作物・資材マスター** を登録
   2. **fields** (圃場) を登録
   3. 各圃場に **cultivation_plans** を作成（`crop_rotations` は空でも可）
   4. 以降、**work_records / auto_tasks** を随時追加

4. **`auto_tasks` コレクションの取り扱い**
   - シンプル運用の場合は `work_records` に `status: "pending" | "completed"` を追加し 1 本化しても良い。
   - 分割する場合は `auto_tasks` は未実施タスク専用コレクションとして扱う。

5. **ユーザー／テナント識別**
   - マルチ農場運用を想定する場合、全コレクションに `owner_id` を追加し複合インデックス `(owner_id, …)` を設定。
   - 単一農場なら不要。

6. **ステップ入力 UI の推奨**
   - 播種→定植→収穫と段階的にデータが埋まるため、入力フォームは工程ごとに分ける。
   - 例：播種予定日のみ先入力し、実施後に実績日を追加する。

---

> **補足**: 以上 6 点を踏まえることで、Airtable からの移行を前提とせずとも、新規ユーザーがゼロから MongoDB にデータを積み上げていく運用がスムーズになります。 