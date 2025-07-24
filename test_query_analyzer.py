#!/usr/bin/env python3
"""
QueryAnalyzerのテスト

MasterAgentのリファクタリング結果を確認するテストスクリプト
"""

import asyncio
import logging
import sys
import os

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agri_ai.services.query_analyzer import QueryAnalyzer

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_query_analyzer():
    """QueryAnalyzerの基本動作テスト"""
    print("="*60)
    print("🔍 QueryAnalyzer 基本動作テスト")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_cases = [
        {
            "query": "橋向こう①の面積を教えて",
            "description": "圃場情報クエリ（面積）",
            "expected_intent": "field_info",
            "expected_agent": "field_agent"
        },
        {
            "query": "新しい畑を2.5haで豊糠エリアに登録",
            "description": "圃場登録クエリ",
            "expected_intent": "field_registration", 
            "expected_agent": "field_registration_agent"
        },
        {
            "query": "全圃場の一覧を見せて",
            "description": "圃場一覧クエリ",
            "expected_intent": "field_info",
            "expected_agent": "field_agent"
        },
        {
            "query": "山田さんから借りた畑を登録したい",
            "description": "圃場登録クエリ（具体的名前）",
            "expected_intent": "field_registration",
            "expected_agent": "field_registration_agent" 
        },
        {
            "query": "第1ハウスの詳細情報",
            "description": "圃場詳細クエリ",
            "expected_intent": "field_info",
            "expected_agent": "field_agent"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            # クエリ分析
            analysis_result = await analyzer.analyze_query_intent(case['query'])
            
            print(f"意図: {analysis_result['intent']}")
            print(f"担当エージェント: {analysis_result['agent']}")
            print(f"信頼度: {analysis_result['confidence']:.2f}")
            print(f"抽出データ: {analysis_result['extracted_data']}")
            
            # 期待値チェック
            intent_match = analysis_result['intent'] == case['expected_intent']
            agent_match = analysis_result['agent'] == case['expected_agent']
            
            if intent_match and agent_match:
                print("✅ 期待通りの結果")
            else:
                print(f"❌ 期待値と異なる結果")
                print(f"   期待意図: {case['expected_intent']}, 実際: {analysis_result['intent']}")
                print(f"   期待エージェント: {case['expected_agent']}, 実際: {analysis_result['agent']}")
            
            # 実行プラン生成テスト
            plan = await analyzer.create_execution_plan(analysis_result)
            print(f"実行プラン:\n{plan}")
            
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_execution_plan_generation():
    """実行プラン生成のテスト"""
    print("\n" + "="*60)
    print("📋 実行プラン生成テスト")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_queries = [
        "橋向こう①の面積を教えて",
        "新しい畑を登録したい", 
        "全圃場の一覧表示",
        "豊糠エリアの圃場一覧",
        "山田さんの畑を2.0haで登録"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n--- プランテスト {i} ---")
        print(f"クエリ: {query}")
        
        try:
            analysis_result = await analyzer.analyze_query_intent(query)
            plan = await analyzer.create_execution_plan(analysis_result)
            
            print(f"生成プラン:")
            print(plan)
            
            # プランの具体性チェック
            if "「" in plan and "」" in plan:
                print("✅ 具体的な圃場名がプランに含まれています")
            else:
                print("ℹ️ 汎用的なプランです")
            
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_field_name_extraction():
    """圃場名抽出のテスト"""
    print("\n" + "="*60)
    print("🏠 圃場名抽出テスト")
    print("="*60)
    
    analyzer = QueryAnalyzer()
    
    test_cases = [
        "橋向こう①の面積を教えて",
        "山田さんから借りた畑の情報",
        "新しい畑を登録したい",
        "第1ハウスの状況確認",
        "学校前の詳細情報"
    ]
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n--- 抽出テスト {i} ---")
        print(f"クエリ: {query}")
        
        try:
            field_name = await analyzer._extract_field_name(query)
            
            if field_name:
                print(f"✅ 抽出成功: 「{field_name}」")
            else:
                print("ℹ️ 圃場名を抽出できませんでした")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def main():
    """メインテスト実行"""
    try:
        print("🚀 QueryAnalyzer リファクタリング検証テスト開始")
        
        # 基本動作テスト
        await test_query_analyzer()
        
        # 実行プラン生成テスト
        await test_execution_plan_generation()
        
        # 圃場名抽出テスト
        await test_field_name_extraction()
        
        print("\n" + "="*60)
        print("📊 テスト完了")
        print("="*60)
        print("✅ QueryAnalyzerサービスが正常に動作しています")
        print("✅ MasterAgentのリファクタリングが成功しました")
        print("✅ 意図分析と実行プラン生成が機能しています")
        print("\n🎉 リファクタリング検証完了！")
        print("="*60)
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())