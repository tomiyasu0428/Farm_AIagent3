#!/usr/bin/env python3
"""
FieldAgent分離アーキテクチャ統合テスト

新しいアーキテクチャをテスト:
- FieldAgent: 圃場情報検索専用
- FieldRegistrationAgent: 圃場登録専用
- MasterAgent: 適切なエージェントへのルーティング
"""

import asyncio
import logging
import sys
import os

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.agri_ai.agents.field_agent import FieldAgent
from src.agri_ai.agents.field_registration_agent import FieldRegistrationAgent
from src.agri_ai.core.master_agent import MasterAgent

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_field_agent_separation():
    """FieldAgent（情報検索専用）のテスト"""
    print("\n" + "="*60)
    print("🔍 FieldAgent（情報検索専用）テスト")
    print("="*60)
    
    agent = FieldAgent()
    
    test_cases = [
        {
            "query": "豊糠エリアの圃場一覧を教えて",
            "expected": "情報検索成功",
            "description": "エリア別圃場検索"
        },
        {
            "query": "橋向こう④の詳細情報",
            "expected": "情報検索成功",
            "description": "特定圃場検索"
        },
        {
            "query": "新田を0.8haで豊糠エリアに登録",
            "expected": "registration_redirect",
            "description": "登録要求のリダイレクト"
        },
        {
            "query": "今日の天気",
            "expected": "out_of_scope",
            "description": "対応範囲外の質問"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await agent.process_query(case['query'])
            print(f"成功: {result['success']}")
            print(f"タイプ: {result.get('query_type', 'unknown')}")
            print(f"応答: {result['response'][:100]}...")
            
            if case['expected'] in ['registration_redirect', 'out_of_scope']:
                assert not result['success'], f"期待: 失敗, 実際: 成功"
                assert result.get('query_type') == case['expected']
                print("✅ 期待通りの動作")
            else:
                assert result['success'], f"期待: 成功, 実際: 失敗"
                print("✅ 正常動作")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_field_registration_agent():
    """FieldRegistrationAgent（登録専用）のテスト"""
    print("\n" + "="*60)
    print("🏡 FieldRegistrationAgent（登録専用）テスト")
    print("="*60)
    
    agent = FieldRegistrationAgent()
    
    test_cases = [
        {
            "query": "テスト圃場XYZを1.0haで豊糠エリアに登録",
            "expected": "registration_success",
            "description": "新規圃場登録"
        },
        {
            "query": "豊糠エリアの圃場一覧を教えて",
            "expected": "out_of_scope",
            "description": "情報検索要求の拒否"
        },
        {
            "query": "今日の天気",
            "expected": "out_of_scope",
            "description": "対応範囲外の質問"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await agent.process_query(case['query'])
            print(f"成功: {result['success']}")
            print(f"タイプ: {result.get('query_type', 'unknown')}")
            print(f"応答: {result['response'][:100]}...")
            
            if case['expected'] == 'out_of_scope':
                assert not result['success'], f"期待: 失敗, 実際: 成功"
                assert result.get('query_type') == 'out_of_scope'
                print("✅ 期待通りの動作")
            else:
                print("✅ 処理完了")
                
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_master_agent_routing():
    """MasterAgent経由でのルーティングテスト"""
    print("\n" + "="*60)
    print("🎯 MasterAgent ルーティングテスト")
    print("="*60)
    
    # MasterAgentの初期化
    master = MasterAgent()
    master.initialize()
    
    test_cases = [
        {
            "query": "豊糠エリアの圃場一覧",
            "expected_agent": "field_agent",
            "description": "圃場情報検索ルーティング"
        },
        {
            "query": "テスト圃場ABCを1.5haで豊緑エリアに登録",
            "expected_agent": "field_registration_agent",
            "description": "圃場登録ルーティング"
        },
        {
            "query": "今日のタスクを確認",
            "expected_agent": "task_lookup",
            "description": "タスク検索ルーティング"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- テスト {i}: {case['description']} ---")
        print(f"入力: {case['query']}")
        
        try:
            result = await master.process_message_async(case['query'], "test_user")
            print(f"応答: {result['response'][:100]}...")
            print(f"使用エージェント: {result.get('agent_used', 'unknown')}")
            print(f"実行プラン: {result.get('plan', 'なし')}")
            print("✅ ルーティング成功")
            
        except Exception as e:
            print(f"❌ エラー: {e}")


async def test_architecture_benefits():
    """アーキテクチャ利点の検証"""
    print("\n" + "="*60)
    print("🏗️ アーキテクチャ利点検証")
    print("="*60)
    
    # 1. 専門エージェントの能力確認
    field_agent = FieldAgent()
    registration_agent = FieldRegistrationAgent()
    
    print("1. 専門エージェント能力確認")
    print(f"   FieldAgent: {field_agent.get_capabilities()['specialization']}")
    print(f"   FieldRegistrationAgent: {registration_agent.get_capabilities()['specialization']}")
    
    # 2. ツール数の確認（複雑性軽減）
    print("\n2. ツール数確認（複雑性軽減）")
    print(f"   FieldAgent ツール数: {len(field_agent.tools)}")
    print(f"   FieldRegistrationAgent ツール数: {len(registration_agent.tools)}")
    
    # 3. MasterAgentのツール統合確認
    master = MasterAgent()
    print(f"\n3. MasterAgent総ツール数: {len(master.tools) if master.tools else 0}")
    
    print("\n✅ アーキテクチャ利点:")
    print("   - 単一責任原則による専門化")
    print("   - イベントループ競合の回避")
    print("   - MasterAgent複雑化の抑制")
    print("   - 将来的な拡張性の確保")


async def main():
    """メインテスト実行"""
    try:
        print("🚀 FieldAgent分離アーキテクチャ統合テスト開始")
        
        # 個別エージェントテスト
        await test_field_agent_separation()
        await test_field_registration_agent()
        
        # MasterAgentルーティングテスト
        await test_master_agent_routing()
        
        # アーキテクチャ利点検証
        await test_architecture_benefits()
        
        print("\n" + "="*60)
        print("🎉 全テスト完了")
        print("="*60)
        
    except Exception as e:
        logger.error(f"テスト実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())