#!/usr/bin/env python3
"""
作業提案ツールのテストスクリプト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.core.agent import agri_agent

# 環境変数を読み込み
load_dotenv()

async def test_work_suggestion_tool():
    """作業提案ツールのテスト"""
    try:
        print("🌱 作業提案ツールのテストを開始します...")
        
        # エージェントの初期化
        await agri_agent.initialize()
        print("✅ エージェント初期化成功")
        
        # テストクエリ
        test_queries = [
            "防除薬剤のローテーション提案をして",
            "天候を考慮した作業計画を教えて",
            "来週の作業提案をお願いします",
            "生育段階に応じた作業を提案して",
            "季節の作業提案を教えて"
        ]
        
        print("\n🔍 作業提案ツールのテストシナリオ:")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- テスト {i}: {query} ---")
            
            try:
                response = await agri_agent.process_message(query, "test_user_001")
                print(f"🤖 AI回答:")
                print(response)
                print(f"✅ テスト {i} 完了")
            except Exception as e:
                print(f"❌ テスト {i} エラー: {e}")
            
            print("-" * 60)
        
        print("\n✅ すべての作業提案テストが完了しました！")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await agri_agent.shutdown()

if __name__ == "__main__":
    asyncio.run(test_work_suggestion_tool())