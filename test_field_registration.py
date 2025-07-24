#!/usr/bin/env python3
"""
圃場登録機能のテストスクリプト
豊糠エリアのデータでユーザーフレンドリーな登録をテスト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.core.master_agent import master_agent

# 環境変数を読み込み
load_dotenv()

async def test_field_registration():
    """圃場登録機能のテスト"""
    try:
        print("🌾 圃場登録機能のテストを開始します...")
        
        # MasterAgentの初期化
        master_agent.initialize()
        print("✅ MasterAgent初期化完了")
        
        # テスト用の自然言語登録クエリ
        test_queries = [
            "橋向こう④を1.5haで豊糠エリアに登録して",
            "学校前圃場を2.3ha、土壌は粘土質で豊糠エリアに追加",
            "新田を0.8haで登録",
            "若菜裏を1.2ha、砂壌土で豊糠エリアに登録",
            "フォレスト③、面積1.8haで登録して"
        ]
        
        print("\n🔍 自然言語での圃場登録テスト:")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- テスト {i} ---")
            print(f"📨 登録指示: {query}")
            
            try:
                # MasterAgentで登録処理
                result = await master_agent.process_message_async(query, "test_user_registration")
                
                # プランがある場合は表示
                if result.get('plan'):
                    print(f"🚀 実行プラン:")
                    print(result['plan'])
                    print()
                
                print(f"🤖 MasterAgent応答:")
                print(result['response'])
                print("✅ テスト完了")
                
            except Exception as e:
                print(f"❌ エラー: {e}")
            
            print("-" * 50)
        
        # 登録後の確認テスト
        print("\n📋 登録後の圃場確認テスト:")
        
        verification_queries = [
            "豊糠エリアの圃場一覧を見せて",
            "橋向こう④の情報を教えて",
            "学校前圃場の面積は？",
            "全圃場の一覧"
        ]
        
        for i, query in enumerate(verification_queries, 1):
            print(f"\n--- 確認テスト {i} ---")
            print(f"📨 確認クエリ: {query}")
            
            try:
                result = await master_agent.process_message_async(query, "test_user_verification")
                print(f"🤖 応答:")
                # 長すぎる場合は切り詰める
                response = result['response']
                if len(response) > 300:
                    response = response[:300] + "..."
                print(response)
                
            except Exception as e:
                print(f"❌ エラー: {e}")
        
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        raise

async def main():
    """メイン処理"""
    await test_field_registration()

if __name__ == "__main__":
    asyncio.run(main())