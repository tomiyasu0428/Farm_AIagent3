#!/usr/bin/env python3
"""
LINE表記改善テスト

改善点:
1. 面積表記をha単位に変更
2. 実行プランをより具体的なタスク内容に変更
"""

import asyncio
import logging
import sys
import os

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agri_ai.core.master_agent import MasterAgent

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_field_area_display():
    """面積表記のテスト（ha単位優先）"""
    print("\n" + "="*60)
    print("📏 面積表記改善テスト（ha単位優先）")
    print("="*60)
    
    # MasterAgentの初期化
    master = MasterAgent()
    master.initialize()
    
    test_cases = [
        {
            "query": "橋向こう①の面積を教えて",
            "expected": "1.2ha",
            "description": "特定圃場の面積（ha表示）"
        },
        {
            "query": "豊糠エリアの圃場一覧",
            "expected": "ha単位での一覧表示",
            "description": "エリア別圃場一覧（ha表示）"
        },
        {
            "query": "第1ハウスの詳細情報",
            "expected": "300㎡（小面積はm²表示）",
            "description": "小面積圃場（m²表示）"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await master.process_message_async(case['query'], "test_user")
            response = result['response']
            
            print(f"応答: {response[:200]}...")
            
            # ha表記の確認
            if "ha" in response:
                print("✅ ha単位での表記確認")
            elif "㎡" in response and ("ハウス" in case['query']):
                print("✅ 小面積でm²表記確認")
            else:
                print("⚠️ 期待する単位表記が見つからない")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_execution_plan_improvements():
    """実行プラン改善テスト"""
    print("\n" + "="*60)
    print("📋 実行プラン改善テスト（具体的タスク表記）")
    print("="*60)
    
    # MasterAgentの初期化
    master = MasterAgent()
    master.initialize()
    
    test_cases = [
        {
            "query": "橋向こう①の面積を教えて",
            "expected_plan": "「橋向こう①」の面積情報をリサーチ",
            "description": "特定圃場の面積問い合わせ"
        },
        {
            "query": "豊糠エリアの圃場一覧",
            "expected_plan": "「豊糠エリア」の圃場一覧をリサーチ",
            "description": "エリア別圃場一覧"
        },
        {
            "query": "新田を0.8haで豊糠エリアに登録",
            "expected_plan": "「新田」を新規圃場として登録処理",
            "description": "圃場登録"
        },
        {
            "query": "今日のタスクを確認",
            "expected_plan": "今日の作業タスクをデータベースから検索",
            "description": "タスク確認"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await master.process_message_async(case['query'], "test_user")
            plan = result.get('plan', '')
            response = result['response']
            
            print(f"実行プラン: {plan}")
            print(f"応答: {response[:100]}...")
            
            # 具体的タスク表記の確認
            if any(keyword in plan for keyword in ["リサーチ", "登録処理", "検索", "レポート"]):
                print("✅ 具体的タスク表記確認")
            else:
                print("⚠️ 具体的タスク表記が不十分")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_line_message_formatting():
    """LINEメッセージフォーマット最適化テスト"""
    print("\n" + "="*60)
    print("💬 LINEメッセージフォーマット最適化テスト")
    print("="*60)
    
    # MasterAgentの初期化
    master = MasterAgent()
    master.initialize()
    
    test_cases = [
        {
            "query": "橋向こう①の詳細情報",
            "description": "詳細情報の簡潔表示",
            "check_points": ["絵文字使用", "簡潔な構成", "ha単位"]
        },
        {
            "query": "第1ハウスの状況",
            "description": "ハウス情報の表示",
            "check_points": ["現在の作物情報", "面積表記", "読みやすさ"]
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await master.process_message_async(case['query'], "test_user")
            response = result['response']
            
            print(f"応答全文:\n{response}")
            
            # チェックポイントの確認
            for point in case['check_points']:
                if point == "絵文字使用" and any(emoji in response for emoji in ["🌾", "🏡", "📋", "🌱"]):
                    print(f"✅ {point}: 確認")
                elif point == "ha単位" and "ha" in response:
                    print(f"✅ {point}: 確認")
                elif point == "簡潔な構成" and len(response.split('\n')) <= 10:
                    print(f"✅ {point}: 確認")
                elif point == "現在の作物情報" and "作物" in response:
                    print(f"✅ {point}: 確認")
                elif point == "読みやすさ" and response.count('\n') >= 2:
                    print(f"✅ {point}: 確認")
                else:
                    print(f"⚠️ {point}: 要改善")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_real_line_scenario():
    """実際のLINEシナリオテスト"""
    print("\n" + "="*60)
    print("📱 実際のLINEシナリオテスト")
    print("="*60)
    
    # 実際のLINE画像と同じクエリをテスト
    master = MasterAgent()
    master.initialize()
    
    query = "橋向こう①の面積を教えて"
    print(f"実際のクエリ: {query}")
    
    try:
        result = await master.process_message_async(query, "test_user")
        plan = result.get('plan', '')
        response = result['response']
        
        print(f"\n🚀 処理開始")
        print(f"\n📋 実行プラン")
        print(plan)
        print(f"\n処理中...")
        print(f"\n最終応答:")
        print(response)
        
        # 改善点の確認
        improvements = []
        if "1.2ha" in response:
            improvements.append("✅ ha単位表記")
        if "橋向こう①" in plan:
            improvements.append("✅ 具体的圃場名をプランに含む")
        if "リサーチ" in plan:
            improvements.append("✅ 具体的タスク表記")
        if len(response) < 200:
            improvements.append("✅ 簡潔な応答")
        
        print(f"\n改善確認:")
        for improvement in improvements:
            print(f"  {improvement}")
            
    except Exception as e:
        print(f"❌ エラー: {e}")


async def main():
    """メインテスト実行"""
    try:
        print("🚀 LINE表記改善テスト開始")
        
        # 面積表記テスト
        await test_field_area_display()
        
        # 実行プラン改善テスト
        await test_execution_plan_improvements()
        
        # LINEメッセージフォーマットテスト
        await test_line_message_formatting()
        
        # 実際のLINEシナリオテスト
        await test_real_line_scenario()
        
        print("\n" + "="*60)
        print("🎉 全テスト完了")
        print("="*60)
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())