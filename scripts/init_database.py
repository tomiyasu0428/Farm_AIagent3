#!/usr/bin/env python3
"""
農業AIデータベースの初期化スクリプト
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# 環境変数を読み込み
load_dotenv()

# Add project root to allow importing from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from add_field_data import add_field_data


async def init_database():
    """データベースの初期化"""
    try:
        print("🌾 農業AIデータベースの初期化を開始します...")
        
        # MongoDB接続
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        database_name = os.getenv("MONGODB_DATABASE_NAME")
        
        client = AsyncIOMotorClient(connection_string)
        db = client[database_name]
        
        # コレクションの作成とサンプルデータの挿入
        await create_crops_collection(db)
        await create_materials_collection(db)
        await create_fields_collection(db)
        await create_scheduled_tasks_collection(db)
        await create_workers_collection(db)
        
        # 圃場データを追加
        await add_field_data()

        print("✅ データベースの初期化が完了しました！")
        
        # 接続を閉じる
        client.close()
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise

async def create_crops_collection(db):
    """作物マスターの作成"""
    print("🌱 作物マスターを作成中...")
    
    crops = db["crops"]
    
    # サンプルデータ
    sample_crops = [
        {
            "name": "トマト",
            "variety": "桃太郎",
            "category": "果菜類",
            "cultivation_calendar": [
                {
                    "stage": "育苗期",
                    "days_from_planting": [0, 30],
                    "key_activities": ["灌水", "温度管理"]
                },
                {
                    "stage": "定植期",
                    "days_from_planting": [30, 40],
                    "key_activities": ["定植", "活着管理"]
                },
                {
                    "stage": "開花期",
                    "days_from_planting": [50, 80],
                    "key_activities": ["防除", "追肥"]
                }
            ],
            "disease_pest_risks": [
                {
                    "name": "疫病",
                    "risk_period": ["5月", "6月", "7月"],
                    "prevention_materials": ["銅水和剤", "ダコニール"]
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "キュウリ",
            "variety": "夏すずみ",
            "category": "果菜類",
            "cultivation_calendar": [
                {
                    "stage": "育苗期",
                    "days_from_planting": [0, 25],
                    "key_activities": ["灌水", "温度管理"]
                }
            ],
            "disease_pest_risks": [
                {
                    "name": "うどんこ病",
                    "risk_period": ["4月", "5月", "9月"],
                    "prevention_materials": ["モレスタン"]
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await crops.insert_many(sample_crops)
    print("  ✅ 作物マスター作成完了")

async def create_materials_collection(db):
    """資材マスターの作成"""
    print("🧪 資材マスターを作成中...")
    
    materials = db["materials"]
    
    # サンプルデータ
    sample_materials = [
        {
            "name": "ダコニール1000",
            "type": "殺菌剤",
            "active_ingredient": "TPN",
            "manufacturer": "SBI ALApromo",
            "dilution_rates": {
                "トマト": "1000倍",
                "キュウリ": "800倍"
            },
            "preharvest_interval": 7,
            "max_applications_per_season": 5,
            "rotation_group": "M",
            "target_diseases": ["疫病", "灰色かび病"],
            "usage_restrictions": {
                "water_source_distance": 100,
                "bee_toxicity": "注意"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "モレスタン水和剤",
            "type": "殺菌剤",
            "active_ingredient": "キノキサリン系",
            "manufacturer": "バイエル",
            "dilution_rates": {
                "キュウリ": "2000倍",
                "トマト": "1500倍"
            },
            "preharvest_interval": 3,
            "max_applications_per_season": 4,
            "rotation_group": "F",
            "target_diseases": ["うどんこ病"],
            "usage_restrictions": {
                "bee_toxicity": "低"
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await materials.insert_many(sample_materials)
    print("  ✅ 資材マスター作成完了")

async def create_fields_collection(db):
    """圃場マスターの作成"""
    print("🚜 圃場マスターを作成中...")
    
    fields = db["fields"]
    crops = db["crops"]
    
    # トマトのObjectIdを取得
    tomato = await crops.find_one({"name": "トマト"})
    tomato_id = tomato["_id"] if tomato else ObjectId()
    
    # サンプルデータ
    sample_fields = [
        {
            "field_code": "A-01",
            "name": "第1ハウス",
            "area": 300,
            "location": {
                "latitude": 35.1234,
                "longitude": 139.5678
            },
            "soil_type": "砂壌土",
            "irrigation_system": "点滴灌漑",
            "current_cultivation": {
                "crop_id": tomato_id,
                "variety": "桃太郎",
                "planting_date": datetime.utcnow() - timedelta(days=60),
                "expected_harvest": datetime.utcnow() + timedelta(days=30),
                "growth_stage": "開花期"
            },
            "next_scheduled_work": {
                "work_type": "防除",
                "scheduled_date": datetime.utcnow() + timedelta(days=1),
                "materials": []
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "field_code": "A-02",
            "name": "第2ハウス",
            "area": 250,
            "location": {
                "latitude": 35.1240,
                "longitude": 139.5680
            },
            "soil_type": "壌土",
            "irrigation_system": "スプリンクラー",
            "current_cultivation": None,
            "next_scheduled_work": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await fields.insert_many(sample_fields)
    print("  ✅ 圃場マスター作成完了")

async def create_scheduled_tasks_collection(db):
    """予定タスクの作成"""
    print("📋 予定タスクを作成中...")
    
    scheduled_tasks = db["scheduled_tasks"]
    fields = db["fields"]
    
    # 第1ハウスのObjectIdを取得
    field1 = await fields.find_one({"field_code": "A-01"})
    field1_id = field1["_id"] if field1 else ObjectId()
    
    # サンプルデータ
    sample_tasks = [
        {
            "field_id": field1_id,
            "scheduled_date": datetime.utcnow() + timedelta(days=1),
            "work_type": "防除",
            "priority": "high",
            "status": "pending",
            "materials": [],
            "notes": "疫病予防のため",
            "auto_generated": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "field_id": field1_id,
            "scheduled_date": datetime.utcnow() + timedelta(days=3),
            "work_type": "灌水",
            "priority": "medium",
            "status": "pending",
            "materials": [],
            "notes": "定期灌水",
            "auto_generated": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await scheduled_tasks.insert_many(sample_tasks)
    print("  ✅ 予定タスク作成完了")

async def create_workers_collection(db):
    """作業者マスターの作成"""
    print("👷 作業者マスターを作成中...")
    
    workers = db["workers"]
    
    # サンプルデータ
    sample_workers = [
        {
            "name": "田中太郎",
            "role": "admin",
            "line_user_id": None,  # 実際のLINE連携時に設定
            "skills": ["防除", "定植", "収穫"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "name": "佐藤花子",
            "role": "worker",
            "line_user_id": None,
            "skills": ["灌水", "除草"],
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await workers.insert_many(sample_workers)
    print("  ✅ 作業者マスター作成完了")

if __name__ == "__main__":
    asyncio.run(init_database())