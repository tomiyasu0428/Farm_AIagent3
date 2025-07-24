"""
圃場情報取得ツール (T4: FieldInfoTool)
"""

from typing import Any, Dict, List
from bson import ObjectId
import logging

from .base_tool import AgriAIBaseTool

logger = logging.getLogger(__name__)


class FieldInfoTool(AgriAIBaseTool):
    """圃場・作付け情報の取得ツール"""

    name: str = "field_info"
    description: str = (
        "圃場の詳細情報や作付け状況を取得します。"
        "使用例: 'A畑の状況', '第1ハウスの作付け情報', '全圃場の状況'"
    )

    async def _execute(self, query: str) -> Dict[str, Any]:
        """圃場情報取得の実行"""
        try:
            # クエリの解析
            field_filter = self._parse_field_query(query)

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                fields_collection = await client.get_collection("fields")

                if field_filter.get("all_fields"):
                    # 全圃場の情報を取得
                    fields = await fields_collection.find({}).to_list(100)
                    return fields, True  # 複数フィールド
                else:
                    # 特定の圃場の情報を取得
                    field = await fields_collection.find_one(field_filter)
                    return field, False  # 単一フィールド

            result, is_multiple = await self._execute_with_db(db_operation)
            
            if is_multiple:
                return await self._format_multiple_fields(result)
            else:
                if result:
                    return await self._format_single_field(result)
                else:
                    return {"error": "指定された圃場が見つかりません"}

        except Exception as e:
            logger.error(f"圃場情報取得エラー: {e}")
            return {"error": f"エラーが発生しました: {str(e)}"}

    def _parse_field_query(self, query: str) -> Dict[str, Any]:
        """クエリから圃場の検索条件を解析"""
        if "全圃場" in query or "すべて" in query or "一覧" in query:
            return {"all_fields": True}
        
        # 豊緑エリア特別対応
        if "豊緑" in query:
            return {"location.region": "豊緑エリア"}

        # 圃場コードやフィールド名での検索パターンを拡張
        field_patterns = {
            # 既存パターン
            "A畑": {"$regex": "A"},
            "B畑": {"$regex": "B"},
            "C畑": {"$regex": "C"},
            "第1": {"$regex": "第1"},
            "第2": {"$regex": "第2"},
            "ハウス": {"$regex": "ハウス"},
            
            # 豊緑エリア圃場パターン
            "橋向こう": {"$regex": "橋向こう"},
            "登山道前": {"$regex": "登山道前"},
            "橋前": {"$regex": "橋前"},
            "田んぼあと": {"$regex": "田んぼあと"},
            "若菜横": {"$regex": "若菜横"},
            "学校裏": {"$regex": "学校裏"},
            "相田さん向かい": {"$regex": "相田さん向かい"},
            "フォレスト": {"$regex": "フォレスト"},
        }

        for pattern, mongo_query in field_patterns.items():
            if pattern in query:
                return {"$or": [{"field_code": mongo_query}, {"name": mongo_query}]}

        # 特定の圃場名で完全一致検索
        return {"name": {"$regex": query, "$options": "i"}}

    async def _format_single_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """単一圃場の情報をフォーマット"""
        # 面積をha単位で表示
        area_m2 = field.get("area", 0)
        area_ha = field.get("area_ha", area_m2 / 10000 if area_m2 > 0 else 0)
        
        # ha単位を優先的に表示
        if area_ha >= 0.01:  # 0.01ha以上ならha表示
            area_display = f"{area_ha:.1f}ha"
        else:
            area_display = f"{area_m2}㎡"
        
        formatted_info = {
            "圃場情報": {
                "圃場コード": field.get("field_code", "不明"),
                "圃場名": field.get("name", "不明"),
                "面積": area_display,
                "土壌タイプ": field.get("soil_type", "不明"),
            }
        }

        # 現在の作付け情報
        current_cultivation = field.get("current_cultivation")
        if current_cultivation:
            # 作物情報を取得
            crop_info = await self._get_crop_info(current_cultivation.get("crop_id"))
            formatted_info["現在の作付け"] = {
                "作物": crop_info.get("name", "不明"),
                "品種": current_cultivation.get("variety", "不明"),
                "定植日": current_cultivation.get("planting_date", "不明"),
                "生育段階": current_cultivation.get("growth_stage", "不明"),
            }

        # 次回作業予定
        next_work = field.get("next_scheduled_work")
        if next_work:
            formatted_info["次回作業予定"] = {
                "作業内容": next_work.get("work_type", "不明"),
                "予定日": next_work.get("scheduled_date", "不明"),
            }

        return formatted_info

    async def _format_multiple_fields(self, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """複数圃場の情報をフォーマット"""
        formatted_info = {"圃場一覧": []}

        for field in fields:
            # 面積をha単位で表示
            area_m2 = field.get("area", 0)
            area_ha = field.get("area_ha", area_m2 / 10000 if area_m2 > 0 else 0)
            
            # ha単位を優先的に表示
            if area_ha >= 0.01:  # 0.01ha以上ならha表示
                area_display = f"{area_ha:.1f}ha"
            else:
                area_display = f"{area_m2}㎡"
            
            field_summary = {
                "圃場コード": field.get("field_code", "不明"),
                "圃場名": field.get("name", "不明"),
                "面積": area_display,
                "エリア": field.get("location", {}).get("region", "不明"),
                "現在の作物": "未作付け",
            }

            # 現在の作付け情報
            current_cultivation = field.get("current_cultivation")
            if current_cultivation:
                crop_info = await self._get_crop_info(current_cultivation.get("crop_id"))
                field_summary["現在の作物"] = crop_info.get("name", "不明")
                field_summary["生育段階"] = current_cultivation.get("growth_stage", "不明")

            formatted_info["圃場一覧"].append(field_summary)

        return formatted_info

    async def _get_crop_info(self, crop_id) -> Dict[str, Any]:
        """作物情報の取得"""
        try:
            if not crop_id:
                return {"name": "不明"}

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                crops_collection = await client.get_collection("crops")
                crop = await crops_collection.find_one({"_id": ObjectId(crop_id)})
                return crop

            crop = await self._execute_with_db(db_operation)
            return crop or {"name": "不明"}
        except Exception as e:
            logger.error(f"作物情報取得エラー: {e}")
            return {"name": "不明"}

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ {result['error']}"

        formatted_lines = []

        # 単一圃場の場合
        if "圃場情報" in result:
            formatted_lines.append("🌾 圃場情報")
            field_info = result["圃場情報"]
            for key, value in field_info.items():
                formatted_lines.append(f"  {key}: {value}")

            if "現在の作付け" in result:
                formatted_lines.append("\n🌱 現在の作付け")
                cultivation = result["現在の作付け"]
                for key, value in cultivation.items():
                    formatted_lines.append(f"  {key}: {value}")

            if "次回作業予定" in result:
                formatted_lines.append("\n📋 次回作業予定")
                next_work = result["次回作業予定"]
                for key, value in next_work.items():
                    formatted_lines.append(f"  {key}: {value}")

        # 複数圃場の場合
        elif "圃場一覧" in result:
            field_count = len(result["圃場一覧"])
            formatted_lines.append(f"🌾 圃場一覧 (合計{field_count}件)")
            
            for i, field in enumerate(result["圃場一覧"], 1):
                formatted_lines.append(f"\n{i}. {field['圃場名']} ({field.get('圃場コード', '不明')})")
                formatted_lines.append(f"   面積: {field['面積']}")
                formatted_lines.append(f"   エリア: {field.get('エリア', '不明')}")
                formatted_lines.append(f"   現在の作物: {field['現在の作物']}")
                if "生育段階" in field:
                    formatted_lines.append(f"   生育段階: {field['生育段階']}")

        return "\n".join(formatted_lines)

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期実行"""
        result = await self._execute(query)
        return self._format_result(result)
