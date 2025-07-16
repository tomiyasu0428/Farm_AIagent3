#!/usr/bin/env python3
"""
テスト用サンプルタスクデータの追加スクリプト
"""

import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bson import ObjectId
from src.agri_ai.database.mongodb_client import mongodb_client

# 環境変数を読み込み
load_dotenv()

async def add_sample_tasks():
    """サンプルタスクデータを追加"""
    try:
        print("🌱 サンプルタスクデータの追加を開始します...")
        
        # MongoDB接続
        await mongodb_client.connect()
        print("✅ MongoDB接続成功")
        
        # scheduled_tasksコレクションを取得
        tasks_collection = await mongodb_client.get_collection("scheduled_tasks")
        
        # 既存のタスクをクリア（テスト用）
        await tasks_collection.delete_many({})
        print("🗑️ 既存のタスクをクリア")
        
        # 今日の日付を基準にサンプルタスクを作成
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        sample_tasks = [
            {
                "_id": ObjectId(),
                "task_id": "TASK-001",
                "field_id": ObjectId("507f1f77bcf86cd799439011"),  # 第1ハウス
                "crop_id": ObjectId("507f1f77bcf86cd799439012"),   # トマト
                "work_type": "防除",
                "description": "第1ハウスのトマト防除作業（疫病対策）",
                "scheduled_date": today,
                "priority": "high",
                "status": "pending",
                "assigned_worker": "田中太郎",
                "estimated_duration": 60,
                "materials_needed": ["ダコニール1000"],
                "notes": "天候が良好な日に実施",
                "created_at": today,
                "updated_at": today
            },
            {
                "_id": ObjectId(),
                "task_id": "TASK-002",
                "field_id": ObjectId("507f1f77bcf86cd799439013"),  # 第2ハウス
                "crop_id": ObjectId("507f1f77bcf86cd799439014"),   # キュウリ
                "work_type": "灌水",
                "description": "第2ハウスの灌水作業",
                "scheduled_date": today,
                "priority": "medium",
                "status": "pending",
                "assigned_worker": "佐藤花子",
                "estimated_duration": 30,
                "materials_needed": [],
                "notes": "午前中に実施",
                "created_at": today,
                "updated_at": today
            },
            {
                "_id": ObjectId(),
                "task_id": "TASK-003",
                "field_id": ObjectId("507f1f77bcf86cd799439011"),  # 第1ハウス
                "crop_id": ObjectId("507f1f77bcf86cd799439012"),   # トマト
                "work_type": "収穫",
                "description": "第1ハウスのトマト収穫作業",
                "scheduled_date": tomorrow,
                "priority": "high",
                "status": "pending",
                "assigned_worker": "田中太郎",
                "estimated_duration": 120,
                "materials_needed": ["収穫コンテナ"],
                "notes": "赤く熟した実のみ収穫",
                "created_at": today,
                "updated_at": today
            },
            {
                "_id": ObjectId(),
                "task_id": "TASK-004",
                "field_id": ObjectId("507f1f77bcf86cd799439013"),  # 第2ハウス
                "crop_id": ObjectId("507f1f77bcf86cd799439014"),   # キュウリ
                "work_type": "防除",
                "description": "第2ハウスのキュウリ防除作業（うどんこ病対策）",
                "scheduled_date": next_week,
                "priority": "medium",
                "status": "pending",
                "assigned_worker": "佐藤花子",
                "estimated_duration": 45,
                "materials_needed": ["モレスタン水和剤"],
                "notes": "薬剤ローテーション実施",
                "created_at": today,
                "updated_at": today
            },
            {
                "_id": ObjectId(),
                "task_id": "TASK-005",
                "field_id": ObjectId("507f1f77bcf86cd799439011"),  # 第1ハウス
                "crop_id": ObjectId("507f1f77bcf86cd799439012"),   # トマト
                "work_type": "整枝",
                "description": "第1ハウスのトマト整枝・誘引作業",
                "scheduled_date": tomorrow,
                "priority": "low",
                "status": "pending",
                "assigned_worker": "田中太郎",
                "estimated_duration": 90,
                "materials_needed": ["誘引ひも", "剪定ばさみ"],
                "notes": "わき芽取りと誘引",
                "created_at": today,
                "updated_at": today
            }
        ]
        
        # サンプルタスクを挿入
        result = await tasks_collection.insert_many(sample_tasks)
        print(f"✅ {len(result.inserted_ids)}個のサンプルタスクを追加しました")
        
        # 追加されたタスクを確認
        print("\n📋 追加されたタスク一覧:")
        async for task in tasks_collection.find({}):
            print(f"- {task['task_id']}: {task['work_type']} ({task['description']})")
            print(f"  予定日: {task['scheduled_date'].strftime('%Y-%m-%d')}")
            print(f"  優先度: {task['priority']}")
            print()
        
        print("🎉 サンプルタスクデータの追加が完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await mongodb_client.disconnect()

if __name__ == "__main__":
    asyncio.run(add_sample_tasks())