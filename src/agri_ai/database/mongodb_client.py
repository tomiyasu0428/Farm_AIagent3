"""
MongoDB接続とクライアント管理
"""

import asyncio
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class MongoDBClient:
    """MongoDB接続クライアント"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self) -> None:
        """MongoDB接続の確立"""
        try:
            self.client = AsyncIOMotorClient(
                settings.mongodb_connection_string,
                serverSelectionTimeoutMS=5000,  # 5秒でタイムアウト
                connectTimeoutMS=10000,         # 10秒でタイムアウト
                maxPoolSize=50,                 # 最大接続プール数
                minPoolSize=5,                  # 最小接続プール数
            )
            
            # 接続テスト
            await self.client.admin.command('ping')
            self.database = self.client[settings.mongodb_database_name]
            
            logger.info("MongoDB接続が正常に確立されました")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB接続エラー: {e}")
            raise
    
    async def disconnect(self) -> None:
        """MongoDB接続の切断"""
        if self.client:
            self.client.close()
            logger.info("MongoDB接続を切断しました")
    
    async def get_collection(self, collection_name: str):
        """指定されたコレクションを取得"""
        if not self.database:
            raise RuntimeError("データベース接続が確立されていません")
        return self.database[collection_name]
    
    async def health_check(self) -> Dict[str, Any]:
        """データベースの健全性チェック"""
        try:
            if not self.client:
                return {"status": "error", "message": "接続未確立"}
            
            # ping test
            await self.client.admin.command('ping')
            
            # サーバー情報取得
            server_info = await self.client.admin.command('serverStatus')
            
            return {
                "status": "healthy",
                "host": server_info.get("host", "unknown"),
                "version": server_info.get("version", "unknown"),
                "uptime": server_info.get("uptime", 0)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}


# グローバルMongoDBクライアントインスタンス
mongodb_client = MongoDBClient()