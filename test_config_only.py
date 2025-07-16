#!/usr/bin/env python3
"""
設定とMongoDB接続のみをテストするスクリプト
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# 環境変数を読み込み
load_dotenv()

async def test_mongodb_connection():
    """MongoDB接続テスト"""
    try:
        print("🔄 MongoDB接続を試行中...")
        
        # 環境変数から接続文字列を取得
        connection_string = os.getenv("MONGODB_CONNECTION_STRING")
        database_name = os.getenv("MONGODB_DATABASE_NAME", "agri_ai")
        
        print(f"📋 データベース名: {database_name}")
        print(f"🔗 接続文字列: {connection_string[:50]}...")
        
        # MongoDB接続
        client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000
        )
        
        # 接続テスト
        await client.admin.command('ping')
        print("✅ MongoDB接続成功！")
        
        # データベースとコレクションの取得
        database = client[database_name]
        test_collection = database["test_collection"]
        
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
        
        # 接続を閉じる
        client.close()
        print("🔐 MongoDB接続を切断しました")
        
        return True
        
    except ConnectionFailure as e:
        print(f"❌ 接続エラー: {e}")
        return False
    except ServerSelectionTimeoutError as e:
        print(f"❌ サーバー選択タイムアウト: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False

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