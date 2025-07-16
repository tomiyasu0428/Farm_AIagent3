#!/usr/bin/env python3
"""
Phase 1 ツールのテストスクリプト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.database.mongodb_client import mongodb_client
from src.agri_ai.langchain_tools.task_lookup_tool import TaskLookupTool
from src.agri_ai.langchain_tools.task_update_tool import TaskUpdateTool
from src.agri_ai.langchain_tools.field_info_tool import FieldInfoTool
from src.agri_ai.langchain_tools.crop_material_tool import CropMaterialTool

# 環境変数を読み込み
load_dotenv()

async def test_phase1_tools():
    """Phase 1 ツールのテスト"""
    try:
        print("🔧 Phase 1 ツールのテストを開始します...")
        
        # MongoDB接続
        await mongodb_client.connect()
        print("✅ MongoDB接続成功")
        
        # 各ツールのテスト
        await test_task_lookup_tool()
        await test_task_update_tool()
        await test_field_info_tool()
        await test_crop_material_tool()
        
        print("\n✅ すべてのツールテストが完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await mongodb_client.disconnect()

async def test_task_lookup_tool():
    """TaskLookupToolのテスト"""
    print("\n📋 TaskLookupToolをテスト中...")
    
    tool = TaskLookupTool()
    
    test_queries = [
        "今日のタスク",
        "明日の作業予定",
        "第1ハウスの防除作業",
        "今週の重要な作業"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        try:
            result = await tool._arun(query)
            print(f"📄 結果: {result[:200]}...")
        except Exception as e:
            print(f"❌ エラー: {e}")
        print("-" * 30)

async def test_task_update_tool():
    """TaskUpdateToolのテスト"""
    print("\n✏️ TaskUpdateToolをテスト中...")
    
    tool = TaskUpdateTool()
    
    test_queries = [
        "防除作業終わりました",
        "第1ハウスの灌水完了",
        "作業を明日に延期します"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        try:
            result = await tool._arun(query)
            print(f"📄 結果: {result[:200]}...")
        except Exception as e:
            print(f"❌ エラー: {e}")
        print("-" * 30)

async def test_field_info_tool():
    """FieldInfoToolのテスト"""
    print("\n🚜 FieldInfoToolをテスト中...")
    
    tool = FieldInfoTool()
    
    test_queries = [
        "第1ハウスの状況",
        "全圃場の状況",
        "A-01の情報"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        try:
            result = await tool._arun(query)
            print(f"📄 結果: {result[:200]}...")
        except Exception as e:
            print(f"❌ エラー: {e}")
        print("-" * 30)

async def test_crop_material_tool():
    """CropMaterialToolのテスト"""
    print("\n🌱 CropMaterialToolをテスト中...")
    
    tool = CropMaterialTool()
    
    test_queries = [
        "トマトに使える農薬",
        "ダコニールの希釈倍率",
        "キュウリの防除薬剤",
        "モレスタンの対象作物"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        try:
            result = await tool._arun(query)
            print(f"📄 結果: {result[:200]}...")
        except Exception as e:
            print(f"❌ エラー: {e}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_phase1_tools())