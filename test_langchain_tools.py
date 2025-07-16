#!/usr/bin/env python3
"""
LangChainツールのテストスクリプト
"""

import asyncio
import os
from dotenv import load_dotenv
from src.agri_ai.database.mongodb_client import mongodb_client
from src.agri_ai.langchain_tools.task_lookup_tool import TaskLookupTool
from src.agri_ai.langchain_tools.field_info_tool import FieldInfoTool

# 環境変数を読み込み
load_dotenv()

async def test_langchain_tools():
    """LangChainツールのテスト"""
    try:
        print("🔧 LangChainツールのテストを開始します...")
        
        # MongoDB接続
        await mongodb_client.connect()
        print("✅ MongoDB接続成功")
        
        # TaskLookupToolのテスト
        await test_task_lookup_tool()
        
        # FieldInfoToolのテスト
        await test_field_info_tool()
        
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
    
    # テストクエリ
    test_queries = [
        "今日のタスク",
        "明日の作業予定",
        "今週のタスク",
        "第1ハウスのタスク"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        result = await tool._arun(query)
        print(f"📄 結果:\n{result}")
        print("-" * 50)

async def test_field_info_tool():
    """FieldInfoToolのテスト"""
    print("\n🚜 FieldInfoToolをテスト中...")
    
    tool = FieldInfoTool()
    
    # テストクエリ
    test_queries = [
        "第1ハウスの状況",
        "第2ハウスの状況",
        "全圃場の状況",
        "A-01の情報"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        result = await tool._arun(query)
        print(f"📄 結果:\n{result}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_langchain_tools())