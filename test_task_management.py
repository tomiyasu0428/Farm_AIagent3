#!/usr/bin/env python3
"""
タスク管理機能（完了報告・延期）のテストスクリプト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.core.agent import agri_agent

# 環境変数を読み込み
load_dotenv()

async def test_task_management():
    """タスク管理機能のテスト"""
    try:
        print("📋 タスク管理機能のテストを開始します...")
        
        # エージェントの初期化
        await agri_agent.initialize()
        print("✅ エージェント初期化成功")
        
        # テストシナリオ
        test_scenarios = [
            {
                "name": "今日のタスク確認",
                "query": "今日のタスクを教えて",
                "expected": "今日の予定されているタスクの一覧"
            },
            {
                "name": "特定タスクの確認",
                "query": "第1ハウスの防除作業について",
                "expected": "第1ハウスの防除作業の詳細"
            },
            {
                "name": "作業完了報告",
                "query": "防除作業終わりました",
                "expected": "作業完了の確認と次回作業の提案"
            },
            {
                "name": "灌水作業の完了報告",
                "query": "第2ハウスの灌水完了しました",
                "expected": "灌水作業の完了確認"
            },
            {
                "name": "作業延期の報告",
                "query": "収穫作業を明日に延期します",
                "expected": "延期処理の確認"
            },
            {
                "name": "延期後のタスク確認",
                "query": "明日のタスクを確認して",
                "expected": "延期されたタスクを含む明日の予定"
            }
        ]
        
        print("\n🔍 タスク管理機能のテストシナリオ:")
        
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"\n--- シナリオ {i}: {scenario['name']} ---")
            print(f"📝 クエリ: {scenario['query']}")
            print(f"🎯 期待結果: {scenario['expected']}")
            
            try:
                response = await agri_agent.process_message(scenario['query'], "test_user_001")
                print(f"🤖 AI回答:")
                print(response)
                print(f"✅ シナリオ {i} 完了")
            except Exception as e:
                print(f"❌ シナリオ {i} エラー: {e}")
            
            print("-" * 60)
        
        print("\n✅ すべてのタスク管理テストが完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await agri_agent.shutdown()

if __name__ == "__main__":
    asyncio.run(test_task_management())