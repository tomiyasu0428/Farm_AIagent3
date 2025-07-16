#!/usr/bin/env python3
"""
MongoDB接続テストスクリプト
"""

import asyncio
import os
from dotenv import load_dotenv
from src.agri_ai.database.mongodb_client import mongodb_client

# 環境変数を読み込み
load_dotenv()

async def test_mongodb_connection():
    """MongoDB接続テスト"""
    try:
        print("🔄 MongoDB接続を試行中...")
        
        # MongoDB接続
        await mongodb_client.connect()
        print("✅ MongoDB接続成功！")
        
        # ヘルスチェック
        health = await mongodb_client.health_check()
        print(f"📊 データベース状態: {health['status']}")
        
        if health['status'] == 'healthy':
            print(f"🖥️  ホスト: {health['host']}")
            print(f"📋 バージョン: {health['version']}")
            print(f"⏰ アップタイム: {health['uptime']}秒")
        
        # テスト用のコレクションを作成
        test_collection = await mongodb_client.get_collection("test_collection")
        
        # テストドキュメントを挿入
        test_doc = {"message": "Hello MongoDB!", "timestamp": "2024-07-16"}
        result = await test_collection.insert_one(test_doc)
        print(f"📝 テストドキュメント挿入成功: {result.inserted_id}")
        
        # ドキュメントを読み取り
        doc = await test_collection.find_one({"_id": result.inserted_id})
        print(f"📖 テストドキュメント読み取り: {doc['message']}")
        
        # テストドキュメントを削除
        await test_collection.delete_one({"_id": result.inserted_id})
        print("🗑️  テストドキュメント削除完了")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        return False
    finally:
        # 接続を閉じる
        await mongodb_client.disconnect()
        print("🔐 MongoDB接続を切断しました")
    
    return True

if __name__ == "__main__":
    print("🌾 農業AI MongoDB接続テスト")
    print("=" * 40)
    
    success = asyncio.run(test_mongodb_connection())
    
    if success:
        print("\n✅ すべてのテストが成功しました！")
        print("🚀 Phase 1の開発を開始できます。")
    else:
        print("\n❌ テストに失敗しました。")
        print("🔧 設定を確認してください。")