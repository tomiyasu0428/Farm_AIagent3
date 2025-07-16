"""
データアクセス共通レイヤー
各ツールで共通して使用されるデータベース操作を提供します。
"""

import logging
from typing import Dict, Any, List, Optional
from bson import ObjectId
from .mongodb_client import MongoDBClient

logger = logging.getLogger(__name__)

class DataAccessLayer:
    """データアクセス共通レイヤー"""
    
    def __init__(self, mongodb_client: MongoDBClient):
        self.mongodb_client = mongodb_client
    
    async def _get_collection(self, collection_name: str):
        """コレクション取得の共通メソッド"""
        return self.mongodb_client.get_collection(collection_name)
    
    async def get_field_info(self, field_id: ObjectId) -> Dict[str, Any]:
        """圃場情報取得の共通メソッド"""
        try:
            fields_collection = await self._get_collection("fields")
            field_info = await fields_collection.find_one({"_id": field_id})
            
            if not field_info:
                return {}
            
            # 現在の栽培情報を取得
            if field_info.get("current_cultivation"):
                crop_info = await self.get_crop_info(field_info["current_cultivation"]["crop_id"])
                field_info["current_cultivation"]["crop_name"] = crop_info.get("name", "不明")
            
            return field_info
            
        except Exception as e:
            logger.error(f"圃場情報取得エラー: {e}")
            return {}
    
    async def get_field_ids_by_name(self, field_filter: Dict[str, Any]) -> List[ObjectId]:
        """圃場ID取得の共通メソッド"""
        try:
            fields_collection = await self._get_collection("fields")
            fields = await fields_collection.find(field_filter).to_list(None)
            return [field["_id"] for field in fields]
            
        except Exception as e:
            logger.error(f"圃場ID取得エラー: {e}")
            return []
    
    async def get_crop_info(self, crop_id: ObjectId) -> Dict[str, Any]:
        """作物情報取得の共通メソッド"""
        try:
            crops_collection = await self._get_collection("crops")
            crop_info = await crops_collection.find_one({"_id": crop_id})
            return crop_info or {}
            
        except Exception as e:
            logger.error(f"作物情報取得エラー: {e}")
            return {}
    
    async def get_crop_name(self, crop_id: ObjectId) -> str:
        """作物名取得の共通メソッド"""
        crop_info = await self.get_crop_info(crop_id)
        return crop_info.get("name", "不明")
    
    async def get_material_info(self, material_id: ObjectId) -> Dict[str, Any]:
        """資材情報取得の共通メソッド"""
        try:
            materials_collection = await self._get_collection("materials")
            material_info = await materials_collection.find_one({"_id": material_id})
            return material_info or {}
            
        except Exception as e:
            logger.error(f"資材情報取得エラー: {e}")
            return {}