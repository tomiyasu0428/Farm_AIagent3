#!/usr/bin/env python3
"""
クエリ解析のテストスクリプト
"""

from src.agri_ai.utils.query_parser import query_parser

def test_query_parser():
    """クエリ解析のテスト"""
    print("🔧 クエリ解析テストを開始します...")
    
    # テストクエリ
    test_queries = [
        "今日のタスク",
        "明日の作業予定",
        "今週のタスク",
        "A畑の今日のタスク",
        "第1ハウスの防除作業",
        "緊急の作業",
        "全圃場の状況",
        "来週の重要な作業",
        "防除と灌水の作業",
        "2024年7月20日の作業"
    ]
    
    for query in test_queries:
        print(f"\n🔍 クエリ: '{query}'")
        result = query_parser.parse_comprehensive_query(query)
        
        print(f"📄 解析結果:")
        for component_type, component_data in result.get("parsed_components", {}).items():
            print(f"  {component_type}: {component_data}")
        
        if not result.get("parsed_components"):
            print("  解析できませんでした")
        
        print("-" * 50)

if __name__ == "__main__":
    test_query_parser()