#!/usr/bin/env python3
"""
圃場データをMongoDBに追加するスクリプト
画像から読み取った豊緑エリアの圃場データを追加
"""

import asyncio
from datetime import datetime
from dotenv import load_dotenv
from src.agri_ai.database.mongodb_client import create_mongodb_client

# 環境変数を読み込み
load_dotenv()

# 画像から読み取った圃場データ
FIELD_DATA = [
    {"name": "橋向こう①", "area_ha": 1.2},
    {"name": "橋向こう②", "area_ha": 2.5},
    {"name": "橋向こう③", "area_ha": 3.1},
    {"name": "登山道前①", "area_ha": 3.6},
    {"name": "登山道前②", "area_ha": 1.0},
    {"name": "登山道前③", "area_ha": 3.9},
    {"name": "橋前", "area_ha": 7.9},
    {"name": "田んぼあと", "area_ha": 0.6},
    {"name": "若菜横", "area_ha": 1.8},
    {"name": "学校裏①", "area_ha": 3.1},
    {"name": "学校裏②", "area_ha": 2.0},
    {"name": "相田さん向かい①", "area_ha": 1.2},
    {"name": "相田さん向かい②", "area_ha": 0.2},
    {"name": "相田さん向かい③", "area_ha": 0.2},
    {"name": "フォレスト①", "area_ha": 0.8},
    {"name": "フォレスト②", "area_ha": 1.5},
]

async def add_field_data():
    """MongoDBに圃場データを追加"""
    client = None
    try:
        print("🌾 豊緑エリア圃場データをMongoDBに追加します...")
        
        # MongoDB接続
        client = create_mongodb_client()
        await client.connect()
        
        fields_collection = await client.get_collection("fields")
        
        # 既存データのfield_codeの最大値を取得
        existing_fields = await fields_collection.find({}).to_list(1000)
        existing_codes = []
        for field in existing_fields:
            code = field.get("field_code", "")
            if code.startswith("TOYOMIDORI-"):
                try:
                    num = int(code.split("-")[1])
                    existing_codes.append(num)
                except:
                    pass
        
        next_code_num = max(existing_codes) + 1 if existing_codes else 1
        
        added_count = 0
        for i, field_info in enumerate(FIELD_DATA):
            field_code = f"TOYOMIDORI-{next_code_num + i:03d}"
            
            # 既存チェック
            existing = await fields_collection.find_one({"name": field_info["name"]})
            if existing:
                print(f"⚠️  {field_info['name']} は既に存在します。スキップ")
                continue
            
            # 新しい圃場データを作成
            field_document = {
                "field_code": field_code,
                "name": field_info["name"],
                "area": field_info["area_ha"] * 10000,  # haを㎡に変換
                "area_ha": field_info["area_ha"],
                "area_unit": "㎡",
                "soil_type": "不明",  # 後で更新可能
                "location": {
                    "region": "豊緑エリア",
                    "address": "詳細住所未設定"
                },
                "current_cultivation": None,  # 現在の作付けなし
                "cultivation_history": [],
                "next_scheduled_work": None,
                "irrigation_system": "不明",
                "greenhouse_type": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "status": "active",
                "notes": "画像データから追加された圃場"
            }
            
            # データベースに挿入
            result = await fields_collection.insert_one(field_document)
            print(f"✅ {field_info['name']} を追加しました (ID: {result.inserted_id})")
            print(f"   圃場コード: {field_code}")
            print(f"   面積: {field_info['area_ha']}ha ({field_info['area_ha'] * 10000}㎡)")
            added_count += 1
        
        print(f"\n🎉 合計 {added_count} 件の圃場データを追加しました！")
        print(f"📊 豊緑エリア総面積: {sum(f['area_ha'] for f in FIELD_DATA):.1f}ha")
        
        # 追加後の確認
        print("\n📋 追加された圃場データの確認:")
        toyomidori_fields = await fields_collection.find(
            {"field_code": {"$regex": "^TOYOMIDORI-"}}
        ).to_list(100)
        
        for field in sorted(toyomidori_fields, key=lambda x: x["field_code"]):
            print(f"  {field['field_code']}: {field['name']} ({field['area_ha']}ha)")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        if client:
            await client.disconnect()

async def verify_field_agent_integration():
    """FieldAgentが新しい圃場データを正しく取得できるか確認"""
    try:
        print("\n🤖 FieldAgentでの新圃場データ取得テスト...")
        
        from src.agri_ai.agents.field_agent import FieldAgent
        
        field_agent = FieldAgent()
        
        # テストクエリ
        test_queries = [
            "豊緑エリアの圃場一覧",
            "橋前の圃場情報",
            "フォレスト①の面積",
            "全圃場の一覧"
        ]
        
        for query in test_queries:
            print(f"\n--- テスト: {query} ---")
            result = await field_agent.process_query(query)
            if result["success"]:
                print("✅ 成功")
                # 応答の一部を表示（長すぎる場合は切り詰め）
                response = result["response"]
                if len(response) > 200:
                    response = response[:200] + "..."
                print(f"応答: {response}")
            else:
                print(f"❌ 失敗: {result['response']}")
                
    except Exception as e:
        print(f"❌ FieldAgentテストエラー: {e}")

async def main():
    """メイン処理"""
    await add_field_data()
    await verify_field_agent_integration()

if __name__ == "__main__":
    asyncio.run(main())