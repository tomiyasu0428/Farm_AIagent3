#!/usr/bin/env python3
"""
エージェント統合テストスクリプト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.core.agent import agri_agent

# 環境変数を読み込み
load_dotenv()

async def test_agent_integration():
    """エージェントの統合テスト"""
    try:
        print("🤖 農業AIエージェントの統合テストを開始します...")
        
        # エージェントの初期化
        await agri_agent.initialize()
        print("✅ エージェント初期化成功")
        
        # テストクエリ
        test_queries = [
            "第1ハウスの状況を教えて",
            "今日のタスクはありますか？",
            "トマトに使える農薬を教えて",
            "全圃場の状況を見せて"
        ]
        
        print("\n🔍 Gemini 2.5 Flashとの対話テスト:")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- テスト {i}: {query} ---")
            try:
                response = await agri_agent.process_message(query, "test_user_001")
                print(f"🤖 回答: {response}")
            except Exception as e:
                print(f"❌ エラー: {e}")
            print("-" * 50)
        
        print("\n✅ すべてのテストが完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await agri_agent.shutdown()

if __name__ == "__main__":
    asyncio.run(test_agent_integration())