#!/usr/bin/env python3
"""
P16 包括的QAテストスクリプト
"""

import asyncio
from dotenv import load_dotenv
from src.agri_ai.core.agent import agri_agent

# 環境変数を読み込み
load_dotenv()

async def test_comprehensive_qa():
    """包括的QAテスト"""
    try:
        print("🔍 包括的QAテストを開始します...")
        
        # エージェントの初期化
        await agri_agent.initialize()
        print("✅ エージェント初期化成功")
        
        # QAテストクエリ（農業関連の様々なシナリオ）
        qa_test_cases = [
            {
                "category": "タスク管理",
                "queries": [
                    "今日やるべき作業は何ですか？",
                    "明日の予定を教えて",
                    "防除作業が終わりました",
                    "作業を来週に延期したいです"
                ]
            },
            {
                "category": "圃場情報",
                "queries": [
                    "第1ハウスの現在の状況は？",
                    "すべての圃場の様子を見せて",
                    "トマトの生育状況はどうですか？",
                    "A-01の詳細情報を教えて"
                ]
            },
            {
                "category": "農薬・資材",
                "queries": [
                    "トマトに使える農薬は？",
                    "ダコニール1000の使い方を教えて",
                    "キュウリの防除薬剤を知りたい",
                    "希釈倍率が分からない"
                ]
            },
            {
                "category": "一般的な質問",
                "queries": [
                    "おはようございます",
                    "今日は何をすればいいですか？",
                    "作業で困っています",
                    "お疲れ様でした"
                ]
            },
            {
                "category": "エラー処理",
                "queries": [
                    "存在しない圃場について教えて",
                    "不明な農薬の情報を教えて",
                    "意味不明な文字列 xkjlsfd",
                    ""  # 空文字列
                ]
            }
        ]
        
        total_tests = 0
        successful_tests = 0
        
        print("\n🔍 包括的QAテスト実行:")
        
        for test_category in qa_test_cases:
            category_name = test_category["category"]
            print(f"\n📂 カテゴリ: {category_name}")
            print("=" * 50)
            
            for i, query in enumerate(test_category["queries"], 1):
                if query == "":
                    query = "[空文字列]"
                
                print(f"\n🔍 テスト {total_tests + 1}: {query}")
                total_tests += 1
                
                try:
                    if query == "[空文字列]":
                        response = await agri_agent.process_message("", "test_user_qa")
                    else:
                        response = await agri_agent.process_message(query, "test_user_qa")
                    
                    print(f"🤖 回答: {response[:200]}...")
                    
                    # 基本的な品質チェック
                    if response and len(response) > 10:
                        successful_tests += 1
                        print("✅ 正常回答")
                    else:
                        print("⚠️ 短すぎる回答")
                    
                except Exception as e:
                    print(f"❌ エラー: {e}")
                
                print("-" * 30)
                
                # レート制限対策
                await asyncio.sleep(0.5)
        
        # 結果サマリー
        print(f"\n📊 QAテスト結果:")
        print(f"総テスト数: {total_tests}")
        print(f"成功: {successful_tests}")
        print(f"失敗: {total_tests - successful_tests}")
        print(f"成功率: {successful_tests/total_tests*100:.1f}%")
        
        if successful_tests / total_tests >= 0.8:
            print("✅ QAテスト合格！（80%以上の成功率）")
        else:
            print("⚠️ QAテスト要改善（80%未満の成功率）")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        await agri_agent.shutdown()

if __name__ == "__main__":
    asyncio.run(test_comprehensive_qa())