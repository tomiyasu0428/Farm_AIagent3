"""
作物-資材対応ツール (T5: CropMaterialTool)
"""

from typing import Any, Dict, Optional
import logging

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser
from ..database.data_access import DataAccessLayer
from ..core.error_handler import ErrorHandler
from pydantic import Field

logger = logging.getLogger(__name__)


class CropMaterialTool(AgriAIBaseTool):
    """作物と資材の対応関係、希釈倍率の取得ツール"""

    name: str = "crop_material"
    description: str = (
        "作物に適用可能な資材や希釈倍率を検索します。"
        "使用例: 'トマトに使える農薬', 'ダコニールの希釈倍率', 'キュウリの防除薬剤'"
    )

    data_access: Any = Field(default=None, exclude=True)

    def __init__(self, mongodb_client_instance=None):
        super().__init__(mongodb_client_instance)
        self.data_access = DataAccessLayer(self.mongodb_client)

    async def _execute(self, query: str) -> Dict[str, Any]:
        """作物-資材対応の実行"""
        try:
            # クエリの種類を判定
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
            return ErrorHandler.handle_tool_error(e, "CropMaterialTool", "作物-資材検索")

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

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                crops_collection = await client.get_collection("crops")
                crop = await crops_collection.find_one({"name": {"$regex": crop_name, "$options": "i"}})
                
                if not crop:
                    return None, None
                
                materials_collection = await client.get_collection("materials")
                applicable_materials = crop.get("applicable_materials", [])
                
                if not applicable_materials:
                    # 作物に直接紐付いた資材がない場合、資材側から検索
                    materials = await materials_collection.find(
                        {f"dilution_rates.{crop_name}": {"$exists": True}}
                    ).to_list(100)
                    return crop, materials
                else:
                    # 適用可能な資材の詳細を取得
                    materials = await materials_collection.find(
                        {"name": {"$in": applicable_materials}}
                    ).to_list(100)
                    return crop, materials

            crop, materials = await self._execute_with_db(db_operation)
            
            if not crop:
                return {"error": f"作物 '{crop_name}' が見つかりませんでした"}

            if not materials:
                return {"error": f"作物 '{crop_name}' に適用可能な資材が見つかりませんでした"}

            # 結果を整形
            result_materials = []
            for material in materials:
                dilution_rate = material.get("dilution_rates", {}).get(crop_name, "不明")

                result_materials.append(
                    {
                        "資材名": material["name"],
                        "種類": material["type"],
                        "希釈倍率": dilution_rate,
                        "有効成分": material.get("active_ingredient", "不明"),
                        "対象病害": material.get("target_diseases", []),
                        "収穫前日数": material.get("preharvest_interval", "不明"),
                        "年間使用制限": material.get("max_applications_per_season", "不明"),
                    }
                )

            return {"crop_name": crop_name, "materials": result_materials, "count": len(result_materials)}

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

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                materials_collection = await client.get_collection("materials")
                material = await materials_collection.find_one(
                    {"name": {"$regex": material_name, "$options": "i"}}
                )
                return material

            material = await self._execute_with_db(db_operation)

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
                    "max_applications": material.get("max_applications_per_season", "不明"),
                }
            else:
                # 全ての作物に対する希釈倍率
                return {
                    "material_name": material["name"],
                    "dilution_rates": dilution_rates,
                    "preharvest_interval": material.get("preharvest_interval", "不明"),
                    "max_applications": material.get("max_applications_per_season", "不明"),
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

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                materials_collection = await client.get_collection("materials")
                material = await materials_collection.find_one(
                    {"name": {"$regex": material_name, "$options": "i"}}
                )
                return material

            material = await self._execute_with_db(db_operation)

            if not material:
                return {"error": f"資材 '{material_name}' が見つかりませんでした"}

            dilution_rates = material.get("dilution_rates", {})
            applicable_crops = list(dilution_rates.keys())

            return {
                "material_name": material["name"],
                "applicable_crops": applicable_crops,
                "dilution_rates": dilution_rates,
                "target_diseases": material.get("target_diseases", []),
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
            # データベース操作を新しい接続で実行
            async def db_operation(client):
                materials_collection = await client.get_collection("materials")
                material = await materials_collection.find_one(
                    {"name": {"$regex": material_name, "$options": "i"}}
                )
                return material

            material = await self._execute_with_db(db_operation)

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
                "target_diseases": material.get("target_diseases", []),
            }

        except Exception as e:
            logger.error(f"特定組み合わせ検索エラー: {e}")
            return {"error": f"検索中にエラーが発生しました: {str(e)}"}

    def _extract_crop_name(self, query: str) -> Optional[str]:
        """クエリから作物名を抽出"""
        return query_parser.extract_crop_name(query)

    def _extract_material_name(self, query: str) -> Optional[str]:
        """クエリから資材名を抽出"""
        # 新しい抽出メソッドを使用
        return query_parser.extract_material_name_from_query(query)

    def _format_result(self, result: Dict[str, Any]) -> str:
        """ツール実行結果を整形"""
        if not result or result.get("error"):
            error_message = result.get("error", "不明なエラーが発生しました")
            if "見つかりませんでした" in error_message:
                return f"ごめんなさい、{error_message}。もう少し詳しく教えていただけますか？"
            return f"❌ 検索中にエラーが発生しました: {error_message}"

        # クエリタイプに基づいて出力を整形
        query_type = self._determine_query_type(result.get("original_query", ""))

        if query_type == "dilution_rate":
            material_name = result.get("material_name", "不明な資材")
            if "crop_name" in result:
                crop_name = result.get("crop_name", "不明な作物")
                dilution_rate = result.get("dilution_rate", "不明")
                return f"✅ {material_name}の{crop_name}に対する希釈倍率は{dilution_rate}です。"
            else:
                rates_str = ", ".join([f"{c}: {r}" for c, r in result.get("dilution_rates", {}).items()])
                return f"✅ {material_name}の希釈倍率:\n{rates_str}"

        if query_type == "material_for_crop":
            crop_name = result.get("crop_name", "不明な作物")
            materials = result.get("materials", [])
            if not materials:
                return f"✅ {crop_name}に適用可能な資材は見つかりませんでした。"

            lines = [f"✅ {crop_name}に使用できる資材は以下の通りです："]
            for mat in materials:
                lines.append(f"  - {mat['資材名']} (希釈倍率: {mat['希釈倍率']})")
            return "\n".join(lines)

        return f"✅ 検索結果:\n{str(result)}"

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期でツールを実行"""
        result = await self._execute(query)
        return self._format_result(result)
