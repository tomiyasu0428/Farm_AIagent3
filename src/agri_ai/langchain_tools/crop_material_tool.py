"""
作物-資材対応ツール (T5: CropMaterialTool)
"""

from typing import Any, Dict, List
from bson import ObjectId
import logging

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser

logger = logging.getLogger(__name__)


class CropMaterialTool(AgriAIBaseTool):
    """作物と資材の対応関係、希釈倍率の取得ツール"""
    
    name: str = "crop_material"
    description: str = (
        "作物に適用可能な資材や希釈倍率を検索します。"
        "使用例: 'トマトに使える農薬', 'ダコニールの希釈倍率', 'キュウリの防除薬剤'"
    )
    
    async def _execute(self, query: str) -> Dict[str, Any]:
        """作物-資材対応の実行"""
        try:
            # クエリの解析
            parsed_query = query_parser.parse_comprehensive_query(query)
            query_type = self._determine_query_type(query)
            
            if query_type == "material_for_crop":
                return await self._get_materials_for_crop(query)
            elif query_type == "dilution_rate":
                return await self._get_dilution_rate(query)
            elif query_type == "crop_for_material":
                return await self._get_crops_for_material(query)
            else:
                return await self._general_search(query)
                
        except Exception as e:
            logger.error(f"作物-資材検索エラー: {e}")
            return {"error": f"エラーが発生しました: {str(e)}"}
    
    def _determine_query_type(self, query: str) -> str:
        """クエリの種類を判定"""
        if any(word in query for word in ["希釈", "倍率", "濃度"]):
            return "dilution_rate"
        elif any(word in query for word in ["使える", "適用", "効果"]):
            return "material_for_crop"
        elif any(word in query for word in ["対象", "作物"]):
            return "crop_for_material"
        else:
            return "general"
    
    async def _get_materials_for_crop(self, query: str) -> Dict[str, Any]:
        """作物に適用可能な資材を取得"""
        try:
            # 作物名を抽出
            crop_name = self._extract_crop_name(query)
            if not crop_name:
                return {"error": "作物名を特定できませんでした"}
            
            # 作物情報を取得
            crops_collection = await self._get_collection("crops")
            crop = await crops_collection.find_one({"name": {"$regex": crop_name, "$options": "i"}})
            
            if not crop:
                return {"error": f"作物 '{crop_name}' が見つかりませんでした"}
            
            # 適用可能な資材を取得
            materials_collection = await self._get_collection("materials")
            applicable_materials = crop.get("applicable_materials", [])
            
            if not applicable_materials:
                # 作物に直接紐付いた資材がない場合、資材側から検索
                materials = await materials_collection.find({
                    f"dilution_rates.{crop_name}": {"$exists": True}
                }).to_list(100)
            else:
                # 作物に紐付いた資材IDから詳細情報を取得
                material_ids = [material["material_id"] for material in applicable_materials]
                materials = await materials_collection.find({"_id": {"$in": material_ids}}).to_list(100)
            
            # 結果を整形
            result_materials = []
            for material in materials:
                dilution_rate = material.get("dilution_rates", {}).get(crop_name, "不明")
                
                result_materials.append({
                    "資材名": material["name"],
                    "種類": material["type"],
                    "希釈倍率": dilution_rate,
                    "有効成分": material.get("active_ingredient", "不明"),
                    "対象病害": material.get("target_diseases", []),
                    "収穫前日数": material.get("preharvest_interval", "不明"),
                    "年間使用制限": material.get("max_applications_per_season", "不明")
                })
            
            return {
                "crop_name": crop_name,
                "materials": result_materials,
                "count": len(result_materials)
            }
            
        except Exception as e:
            logger.error(f"作物用資材検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}
    
    async def _get_dilution_rate(self, query: str) -> Dict[str, Any]:
        """希釈倍率を取得"""
        try:
            # 資材名を抽出
            material_name = self._extract_material_name(query)
            if not material_name:
                return {"error": "資材名を特定できませんでした"}
            
            # 作物名を抽出
            crop_name = self._extract_crop_name(query)
            
            # 資材情報を取得
            materials_collection = await self._get_collection("materials")
            material = await materials_collection.find_one({"name": {"$regex": material_name, "$options": "i"}})
            
            if not material:
                return {"error": f"資材 '{material_name}' が見つかりませんでした"}
            
            dilution_rates = material.get("dilution_rates", {})
            
            if crop_name:
                # 特定の作物に対する希釈倍率
                rate = dilution_rates.get(crop_name, "不明")
                return {
                    "material_name": material["name"],
                    "crop_name": crop_name,
                    "dilution_rate": rate,
                    "preharvest_interval": material.get("preharvest_interval", "不明"),
                    "max_applications": material.get("max_applications_per_season", "不明")
                }
            else:
                # 全ての作物に対する希釈倍率
                return {
                    "material_name": material["name"],
                    "dilution_rates": dilution_rates,
                    "preharvest_interval": material.get("preharvest_interval", "不明"),
                    "max_applications": material.get("max_applications_per_season", "不明")
                }
                
        except Exception as e:
            logger.error(f"希釈倍率検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}
    
    async def _get_crops_for_material(self, query: str) -> Dict[str, Any]:
        """資材に適用可能な作物を取得"""
        try:
            # 資材名を抽出
            material_name = self._extract_material_name(query)
            if not material_name:
                return {"error": "資材名を特定できませんでした"}
            
            # 資材情報を取得
            materials_collection = await self._get_collection("materials")
            material = await materials_collection.find_one({"name": {"$regex": material_name, "$options": "i"}})
            
            if not material:
                return {"error": f"資材 '{material_name}' が見つかりませんでした"}
            
            dilution_rates = material.get("dilution_rates", {})
            applicable_crops = list(dilution_rates.keys())
            
            return {
                "material_name": material["name"],
                "applicable_crops": applicable_crops,
                "dilution_rates": dilution_rates,
                "target_diseases": material.get("target_diseases", [])
            }
            
        except Exception as e:
            logger.error(f"資材対象作物検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}
    
    async def _general_search(self, query: str) -> Dict[str, Any]:
        """一般的な検索"""
        try:
            # 作物名と資材名の両方を抽出
            crop_name = self._extract_crop_name(query)
            material_name = self._extract_material_name(query)
            
            if crop_name and material_name:
                # 両方が指定されている場合、具体的な組み合わせを検索
                return await self._get_specific_combination(crop_name, material_name)
            elif crop_name:
                # 作物のみが指定されている場合
                return await self._get_materials_for_crop(query)
            elif material_name:
                # 資材のみが指定されている場合
                return await self._get_crops_for_material(query)
            else:
                return {"error": "作物名または資材名を指定してください"}
                
        except Exception as e:
            logger.error(f"一般検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}
    
    async def _get_specific_combination(self, crop_name: str, material_name: str) -> Dict[str, Any]:
        """特定の作物と資材の組み合わせを検索"""
        try:
            materials_collection = await self._get_collection("materials")
            material = await materials_collection.find_one({"name": {"$regex": material_name, "$options": "i"}})
            
            if not material:
                return {"error": f"資材 '{material_name}' が見つかりませんでした"}
            
            dilution_rates = material.get("dilution_rates", {})
            dilution_rate = dilution_rates.get(crop_name, "適用不可")
            
            if dilution_rate == "適用不可":
                return {"error": f"'{material_name}' は '{crop_name}' に適用できません"}
            
            return {
                "crop_name": crop_name,
                "material_name": material["name"],
                "dilution_rate": dilution_rate,
                "type": material["type"],
                "preharvest_interval": material.get("preharvest_interval", "不明"),
                "max_applications": material.get("max_applications_per_season", "不明"),
                "target_diseases": material.get("target_diseases", [])
            }
            
        except Exception as e:
            logger.error(f"特定組み合わせ検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}
    
    def _extract_crop_name(self, query: str) -> str:
        """クエリから作物名を抽出"""
        crop_keywords = ["トマト", "キュウリ", "ナス", "ピーマン", "イチゴ", "レタス", "キャベツ", "白菜"]
        
        for crop in crop_keywords:
            if crop in query:
                return crop
        
        return None
    
    def _extract_material_name(self, query: str) -> str:
        """クエリから資材名を抽出"""
        # 一般的な資材名のパターン
        material_patterns = [
            "ダコニール", "モレスタン", "ベンレート", "オーソサイド", 
            "アミスター", "ストロビー", "フルピカ", "トップジン"
        ]
        
        for material in material_patterns:
            if material in query:
                return material
        
        # 数字が含まれる場合（例：ダコニール1000）
        import re
        material_with_number = re.search(r'([ァ-ヶー]+\d*)', query)
        if material_with_number:
            return material_with_number.group(1)
        
        return None
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ {result['error']}"
        
        # 作物用資材の場合
        if result.get("materials"):
            crop_name = result.get("crop_name", "不明")
            materials = result.get("materials", [])
            
            if not materials:
                return f"'{crop_name}' に適用可能な資材が見つかりませんでした"
            
            lines = [f"🌱 {crop_name} に適用可能な資材 ({len(materials)}件):\n"]
            
            for i, material in enumerate(materials, 1):
                lines.append(f"{i}. {material['資材名']} ({material['種類']})")
                lines.append(f"   希釈倍率: {material['希釈倍率']}")
                lines.append(f"   収穫前日数: {material['収穫前日数']}日")
                
                if material['対象病害']:
                    lines.append(f"   対象病害: {', '.join(material['対象病害'])}")
                lines.append("")
            
            return "\n".join(lines)
        
        # 希釈倍率の場合
        elif result.get("dilution_rate"):
            material_name = result.get("material_name", "不明")
            crop_name = result.get("crop_name")
            
            if crop_name:
                lines = [f"💧 {material_name} の希釈倍率:"]
                lines.append(f"   作物: {crop_name}")
                lines.append(f"   希釈倍率: {result['dilution_rate']}")
                lines.append(f"   収穫前日数: {result.get('preharvest_interval', '不明')}日")
                lines.append(f"   年間使用制限: {result.get('max_applications', '不明')}回")
            else:
                lines = [f"💧 {material_name} の希釈倍率:"]
                dilution_rates = result.get("dilution_rates", {})
                for crop, rate in dilution_rates.items():
                    lines.append(f"   {crop}: {rate}")
            
            return "\n".join(lines)
        
        # 資材対象作物の場合
        elif result.get("applicable_crops"):
            material_name = result.get("material_name", "不明")
            crops = result.get("applicable_crops", [])
            
            lines = [f"🧪 {material_name} の適用可能作物:"]
            for crop in crops:
                rate = result.get("dilution_rates", {}).get(crop, "不明")
                lines.append(f"   {crop}: {rate}")
            
            return "\n".join(lines)
        
        else:
            return "検索結果が見つかりませんでした"