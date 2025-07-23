#!/usr/bin/env python3
"""
未知圃場名対応テスト

現在の実装で未知の圃場名がどう処理されるかを確認
"""

import asyncio
import sys
import os

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agri_ai.core.master_agent import MasterAgent


async def test_unknown_field_extraction():
    """未知圃場名の抽出テスト"""
    print("="*60)
    print("🔍 未知圃場名抽出テスト")
    print("="*60)
    
    master = MasterAgent()
    
    test_cases = [
        # 正規表現パターンでキャッチできるケース
        {
            "query": "山田さんの畑の面積",
            "expected": "山田さんの畑",
            "pattern": "r'([^の\\s]+)の面積'"
        },
        {
            "query": "「池の向こう」の詳細情報", 
            "expected": "池の向こう",
            "pattern": "r'「([^」]+)」'"
        },
        {
            "query": "新規テスト圃場を登録",
            "expected": "新規テスト圃場",
            "pattern": "r'([^を\\s]+)を'"
        },
        
        # 正規表現パターンでキャッチできないケース
        {
            "query": "山田さんの畑はどこ？",
            "expected": "",  # 抽出失敗予想
            "pattern": "パターンマッチなし"
        },
        {
            "query": "池の向こうについて教えて",
            "expected": "",  # 抽出失敗予想
            "pattern": "パターンマッチなし"
        },
        {
            "query": "裏の畑の状況確認",
            "expected": "",  # 抽出失敗予想
            "pattern": "パターンマッチなし"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['pattern']} ---")
        print(f"入力: {case['query']}")
        
        # 圃場名抽出をテスト
        extracted = master._extract_field_name(case['query'])
        print(f"抽出結果: '{extracted}'")
        print(f"期待結果: '{case['expected']}'")
        
        if extracted == case['expected']:
            print("✅ 抽出成功" if extracted else "⚠️ 抽出失敗（予想通り）")
        else:
            print("❌ 予想と異なる結果")


async def test_execution_plan_with_unknown_fields():
    """未知圃場名での実行プラン生成テスト"""
    print("\n" + "="*60)
    print("📋 未知圃場名での実行プラン生成テスト")
    print("="*60)
    
    master = MasterAgent()
    
    test_cases = [
        {
            "query": "山田さんの畑の面積を教えて",
            "description": "正規表現でキャッチできる未知圃場名"
        },
        {
            "query": "池の向こうはどこにある？",
            "description": "正規表現でキャッチできない未知圃場名"
        },
        {
            "query": "新しく借りた畑の詳細情報",
            "description": "正規表現でキャッチできない未知圃場名"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        # 実行プラン生成をテスト
        plan = master._create_execution_plan(case['query'])
        print(f"実行プラン:\n{plan}")
        
        # 具体的圃場名がプランに含まれているかチェック
        if "「" in plan and "」" in plan:
            print("✅ 具体的圃場名がプランに含まれている")
        else:
            print("⚠️ 汎用的なプランになっている")


async def test_real_scenarios():
    """実際のシナリオテスト"""
    print("\n" + "="*60)
    print("🎯 実際のシナリオテスト")
    print("="*60)
    
    master = MasterAgent()
    master.initialize()
    
    test_cases = [
        {
            "query": "山田さんの畑の面積を教えて",
            "description": "存在しない圃場の問い合わせ"
        },
        {
            "query": "テスト用新圃場を1.5haで豊糠エリアに登録",
            "description": "未知圃場名での登録"
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
            print(f"応答: {response[:150]}...")
            
        except Exception as e:
            print(f"❌ エラー: {e}")


async def main():
    """メインテスト実行"""
    print("🚀 未知圃場名対応テスト開始")
    
    # 圃場名抽出テスト
    await test_unknown_field_extraction()
    
    # 実行プラン生成テスト
    await test_execution_plan_with_unknown_fields()
    
    # 実際のシナリオテスト
    await test_real_scenarios()
    
    print("\n" + "="*60)
    print("📝 結論")
    print("="*60)
    print("現在の実装:")
    print("✅ 正規表現パターンにマッチする未知圃場名は対応可能")
    print("❌ パターンにマッチしない未知圃場名は汎用プランになる")
    print("💡 改善案: より柔軟な自然言語処理が必要")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())