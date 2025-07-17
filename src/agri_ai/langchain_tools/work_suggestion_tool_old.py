"""
作業提案ツール (P15: WorkSuggestionTool)
"""

from typing import Any, Dict, List
from datetime import datetime, timedelta
from bson import ObjectId
import logging

from .base_tool import AgriAIBaseTool
from ..database.data_access import DataAccessLayer
from ..core.error_handler import ErrorHandler
from pydantic import Field

logger = logging.getLogger(__name__)


class WorkSuggestionTool(AgriAIBaseTool):
    """作業提案・農薬ローテーション管理ツール"""

    name: str = "work_suggestion"
    description: str = (
        "作業提案や農薬ローテーション、天候を考慮した作業計画を提案します。"
        "使用例: '来週の作業提案', '防除薬剤のローテーション', '天候を考慮した作業計画'"
    )

    data_access: Any = Field(default=None, exclude=True)

    def __init__(self, mongodb_client_instance=None):
        super().__init__(mongodb_client_instance)
        self.data_access = DataAccessLayer(self.mongodb_client)

    async def _execute(self, query: str) -> Dict[str, Any]:
        """作業提案の実行"""
        try:
            # クエリの種類を判定
            suggestion_type = self._parse_suggestion_query(query)

            if suggestion_type == "rotation":
                return await self._suggest_pesticide_rotation(query)
            elif suggestion_type == "weather":
                return await self._suggest_weather_based_work(query)
            elif suggestion_type == "weekly":
                return await self._suggest_weekly_work(query)
            elif suggestion_type == "crop_stage":
                return await self._suggest_crop_stage_work(query)
            else:
                return await self._suggest_general_work(query)

        except Exception as e:
            return ErrorHandler.handle_tool_error(e, "WorkSuggestionTool", "作業提案")

    def _parse_suggestion_query(self, query: str) -> str:
        """クエリから提案タイプを判定"""
        if "ローテーション" in query or "薬剤" in query:
            return "rotation"
        elif "天候" in query or "天気" in query:
            return "weather"
        elif "来週" in query or "週間" in query:
            return "weekly"
        elif "生育" in query or "段階" in query:
            return "crop_stage"
        else:
            return "general"

    async def _suggest_pesticide_rotation(self, query: str) -> Dict[str, Any]:
        """農薬ローテーション提案"""
        try:
            # 現在の防除履歴を取得
            tasks_collection = await self._get_collection("scheduled_tasks")

            # 過去30日間の防除作業履歴を取得
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_pesticide_tasks = await tasks_collection.find(
                {"work_type": "防除", "scheduled_date": {"$gte": thirty_days_ago}, "status": "completed"}
            ).to_list(100)

            # 使用済み農薬を集計
            used_pesticides = {}
            for task in recent_pesticide_tasks:
                materials = task.get("materials_needed", [])
                field_id = task.get("field_id")

                if field_id not in used_pesticides:
                    used_pesticides[field_id] = []
                used_pesticides[field_id].extend(materials)

            # 各圃場の作物情報を取得
            fields_collection = await self._get_collection("fields")
            rotation_suggestions = []

            async for field in fields_collection.find({}):
                field_id = field["_id"]
                field_name = field.get("name", "不明")

                # 現在の作物を取得
                current_cultivation = field.get("current_cultivation", {})
                crop_id = current_cultivation.get("crop_id")

                if crop_id:
                    # 作物に適用可能な農薬を取得
                    suggestions = await self._get_rotation_suggestions(
                        crop_id, used_pesticides.get(field_id, [])
                    )

                    rotation_suggestions.append(
                        {"field_name": field_name, "field_id": str(field_id), "suggestions": suggestions}
                    )

            return {
                "type": "pesticide_rotation",
                "suggestions": rotation_suggestions,
                "rotation_principle": "同一系統の農薬を連続使用せず、作用機序の異なる薬剤をローテーションすることで抵抗性を予防します。",
            }

        except Exception as e:
            logger.error(f"農薬ローテーション提案エラー: {e}")
            return {"error": f"農薬ローテーション提案中にエラーが発生しました: {str(e)}"}

    async def _get_rotation_suggestions(
        self, crop_id: ObjectId, used_pesticides: List[str]
    ) -> List[Dict[str, Any]]:
        """作物別の農薬ローテーション提案"""
        try:
            # 作物情報を取得
            crops_collection = await self._get_collection("crops")
            crop = await crops_collection.find_one({"_id": crop_id})

            if not crop:
                return []

            crop_name = crop.get("name", "不明")

            # 作物に適用可能な農薬を取得
            materials_collection = await self._get_collection("materials")
            applicable_materials = await materials_collection.find(
                {"applicable_crops": crop_name, "type": "農薬"}
            ).to_list(100)

            # 使用履歴を考慮したローテーション提案
            suggestions = []

            # 最近使用していない農薬を優先
            for material in applicable_materials:
                material_name = material.get("name", "不明")
                if material_name not in used_pesticides:
                    crop_application = next(
                        (
                            app
                            for app in material.get("crop_applications", [])
                            if app.get("crop") == crop_name
                        ),
                        {},
                    )

                    suggestions.append(
                        {
                            "pesticide_name": material_name,
                            "type": material.get("pesticide_type", "不明"),
                            "dilution_rate": crop_application.get("dilution_rate", "不明"),
                            "target_pests": crop_application.get("target_pests", []),
                            "days_before_harvest": crop_application.get("days_before_harvest", 0),
                            "priority": "推奨" if material_name not in used_pesticides else "通常",
                        }
                    )

            # 最近使用した農薬も含める（参考用）
            for material in applicable_materials:
                material_name = material.get("name", "不明")
                if material_name in used_pesticides:
                    crop_application = next(
                        (
                            app
                            for app in material.get("crop_applications", [])
                            if app.get("crop") == crop_name
                        ),
                        {},
                    )

                    suggestions.append(
                        {
                            "pesticide_name": material_name,
                            "type": material.get("pesticide_type", "不明"),
                            "dilution_rate": crop_application.get("dilution_rate", "不明"),
                            "target_pests": crop_application.get("target_pests", []),
                            "days_before_harvest": crop_application.get("days_before_harvest", 0),
                            "priority": "要注意（最近使用済み）",
                        }
                    )

            return suggestions

        except Exception as e:
            logger.error(f"農薬ローテーション詳細取得エラー: {e}")
            return []

    async def _suggest_weather_based_work(self, query: str) -> Dict[str, Any]:
        """天候を考慮した作業提案"""
        try:
            # 模擬的な天候情報（実際の実装では気象APIを使用）
            weather_conditions = {
                "today": {"condition": "晴れ", "temperature": 28, "humidity": 65, "wind": "弱"},
                "tomorrow": {"condition": "曇り", "temperature": 25, "humidity": 70, "wind": "弱"},
                "day_after": {"condition": "雨", "temperature": 22, "humidity": 85, "wind": "中"},
            }

            # 天候に適した作業を提案
            weather_suggestions = []

            # 今日の提案
            if weather_conditions["today"]["condition"] == "晴れ":
                weather_suggestions.append(
                    {
                        "date": "今日",
                        "weather": weather_conditions["today"],
                        "suitable_work": ["防除作業", "収穫作業", "整枝作業", "除草作業"],
                        "avoid_work": [],
                        "notes": "晴天で作業に適しています。防除作業は風が弱いため効果的です。",
                    }
                )

            # 明日の提案
            if weather_conditions["tomorrow"]["condition"] == "曇り":
                weather_suggestions.append(
                    {
                        "date": "明日",
                        "weather": weather_conditions["tomorrow"],
                        "suitable_work": ["灌水作業", "整枝作業", "収穫作業"],
                        "avoid_work": ["防除作業"],
                        "notes": "曇天で作業しやすい条件です。防除作業は避けた方が良いでしょう。",
                    }
                )

            # 明後日の提案
            if weather_conditions["day_after"]["condition"] == "雨":
                weather_suggestions.append(
                    {
                        "date": "明後日",
                        "weather": weather_conditions["day_after"],
                        "suitable_work": ["室内作業", "機械メンテナンス"],
                        "avoid_work": ["防除作業", "収穫作業", "整枝作業"],
                        "notes": "雨天のため屋外作業は控えてください。室内作業や機械メンテナンスに適しています。",
                    }
                )

            return {
                "type": "weather_based",
                "weather_forecast": weather_conditions,
                "suggestions": weather_suggestions,
                "general_advice": "天候に応じて作業を調整し、農薬散布は無風・晴天時に行うのが効果的です。",
            }

        except Exception as e:
            logger.error(f"天候ベース作業提案エラー: {e}")
            return {"error": f"天候ベース作業提案中にエラーが発生しました: {str(e)}"}

    async def _suggest_weekly_work(self, query: str) -> Dict[str, Any]:
        """週間作業提案"""
        try:
            # 来週の日程を生成
            today = datetime.now()
            next_week_start = today + timedelta(days=(7 - today.weekday()))

            # 既存のタスクを取得
            tasks_collection = await self._get_collection("scheduled_tasks")
            next_week_end = next_week_start + timedelta(days=7)

            existing_tasks = await tasks_collection.find(
                {"scheduled_date": {"$gte": next_week_start, "$lt": next_week_end}, "status": "pending"}
            ).to_list(100)

            # 圃場別の作業提案
            fields_collection = await self._get_collection("fields")
            weekly_suggestions = []

            async for field in fields_collection.find({}):
                field_suggestions = await self._generate_field_weekly_suggestions(field, existing_tasks)
                weekly_suggestions.extend(field_suggestions)

            return {
                "type": "weekly_work",
                "week_start": next_week_start.strftime("%Y-%m-%d"),
                "week_end": next_week_end.strftime("%Y-%m-%d"),
                "suggestions": weekly_suggestions,
                "existing_tasks": len(existing_tasks),
            }

        except Exception as e:
            logger.error(f"週間作業提案エラー: {e}")
            return {"error": f"週間作業提案中にエラーが発生しました: {str(e)}"}

    async def _generate_field_weekly_suggestions(
        self, field: Dict[str, Any], existing_tasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """圃場別の週間作業提案"""
        suggestions = []
        field_name = field.get("name", "不明")

        # 現在の作物情報
        current_cultivation = field.get("current_cultivation", {})
        growth_stage = current_cultivation.get("growth_stage", "不明")

        # 生育段階に応じた作業提案
        if growth_stage == "開花期":
            suggestions.extend(
                [
                    {
                        "field_name": field_name,
                        "work_type": "整枝",
                        "priority": "medium",
                        "reason": "開花期のため整枝・誘引作業が重要です",
                        "estimated_duration": 60,
                    },
                    {
                        "field_name": field_name,
                        "work_type": "灌水",
                        "priority": "high",
                        "reason": "開花期は水分管理が重要です",
                        "estimated_duration": 30,
                    },
                ]
            )
        elif growth_stage == "結実期":
            suggestions.extend(
                [
                    {
                        "field_name": field_name,
                        "work_type": "収穫",
                        "priority": "high",
                        "reason": "結実期のため収穫作業が必要です",
                        "estimated_duration": 120,
                    },
                    {
                        "field_name": field_name,
                        "work_type": "防除",
                        "priority": "medium",
                        "reason": "結実期の病害虫対策が重要です",
                        "estimated_duration": 45,
                    },
                ]
            )

        return suggestions

    async def _suggest_crop_stage_work(self, query: str) -> Dict[str, Any]:
        """生育段階に応じた作業提案"""
        try:
            # 全圃場の生育段階を取得
            fields_collection = await self._get_collection("fields")
            stage_suggestions = []

            async for field in fields_collection.find({}):
                field_name = field.get("name", "不明")
                current_cultivation = field.get("current_cultivation", {})
                growth_stage = current_cultivation.get("growth_stage", "不明")

                if growth_stage != "不明":
                    crop_id = current_cultivation.get("crop_id")
                    crop_name = await self._get_crop_name(crop_id)

                    stage_work = self._get_stage_specific_work(growth_stage, crop_name)

                    stage_suggestions.append(
                        {
                            "field_name": field_name,
                            "crop_name": crop_name,
                            "growth_stage": growth_stage,
                            "recommended_work": stage_work,
                        }
                    )

            return {
                "type": "crop_stage_based",
                "suggestions": stage_suggestions,
                "general_advice": "生育段階に応じた適切な作業を行うことで、品質向上と収量増加が期待できます。",
            }

        except Exception as e:
            logger.error(f"生育段階ベース作業提案エラー: {e}")
            return {"error": f"生育段階ベース作業提案中にエラーが発生しました: {str(e)}"}

    def _get_stage_specific_work(self, growth_stage: str, crop_name: str) -> List[Dict[str, Any]]:
        """生育段階別の作業リスト"""
        stage_work_map = {
            "育苗期": [
                {"work": "水やり", "frequency": "毎日", "importance": "高"},
                {"work": "温度管理", "frequency": "毎日", "importance": "高"},
                {"work": "病害虫チェック", "frequency": "週2回", "importance": "中"},
            ],
            "定植期": [
                {"work": "土壌準備", "frequency": "定植前", "importance": "高"},
                {"work": "定植作業", "frequency": "時期限定", "importance": "高"},
                {"work": "活着促進", "frequency": "定植後1週間", "importance": "高"},
            ],
            "生育期": [
                {"work": "整枝・誘引", "frequency": "週1回", "importance": "高"},
                {"work": "追肥", "frequency": "2週間に1回", "importance": "中"},
                {"work": "病害虫防除", "frequency": "必要に応じて", "importance": "高"},
            ],
            "開花期": [
                {"work": "整枝・誘引", "frequency": "週1回", "importance": "高"},
                {"work": "灌水管理", "frequency": "毎日", "importance": "高"},
                {"work": "受粉促進", "frequency": "必要に応じて", "importance": "中"},
            ],
            "結実期": [
                {"work": "収穫", "frequency": "毎日", "importance": "高"},
                {"work": "整枝", "frequency": "週1回", "importance": "中"},
                {"work": "品質管理", "frequency": "収穫時", "importance": "高"},
            ],
        }

        return stage_work_map.get(growth_stage, [])

    async def _get_crop_name(self, crop_id: ObjectId) -> str:
        """作物名を取得"""
        return await self.data_access.get_crop_name(crop_id)

    async def _suggest_general_work(self, query: str) -> Dict[str, Any]:
        """一般的な作業提案"""
        try:
            # 現在の季節と時期に応じた一般的な作業提案
            current_month = datetime.now().month

            seasonal_work = self._get_seasonal_work(current_month)

            return {
                "type": "general_work",
                "current_month": current_month,
                "seasonal_work": seasonal_work,
                "general_advice": "季節に応じた作業を計画的に実施することで、効率的な農業経営が可能になります。",
            }

        except Exception as e:
            logger.error(f"一般作業提案エラー: {e}")
            return {"error": f"一般作業提案中にエラーが発生しました: {str(e)}"}

    def _get_seasonal_work(self, month: int) -> List[Dict[str, Any]]:
        """季節別の作業リスト"""
        seasonal_work_map = {
            7: [  # 7月
                {"work": "収穫作業", "priority": "高", "note": "夏野菜の収穫時期"},
                {"work": "病害虫防除", "priority": "高", "note": "高温多湿で病害虫が発生しやすい"},
                {"work": "灌水管理", "priority": "高", "note": "水分不足に注意"},
                {"work": "整枝・誘引", "priority": "中", "note": "継続的な管理が必要"},
            ],
            8: [  # 8月
                {"work": "収穫作業", "priority": "高", "note": "夏野菜の収穫最盛期"},
                {"work": "秋作準備", "priority": "中", "note": "秋作物の準備を開始"},
                {"work": "施設管理", "priority": "中", "note": "高温対策が重要"},
            ],
        }

        return seasonal_work_map.get(month, [])

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ {result['error']}"

        result_type = result.get("type", "")
        formatted_lines = []

        if result_type == "pesticide_rotation":
            formatted_lines.append("🔄 農薬ローテーション提案")
            formatted_lines.append("")

            for suggestion in result.get("suggestions", []):
                formatted_lines.append(f"📍 {suggestion['field_name']}")
                for item in suggestion.get("suggestions", []):
                    priority_emoji = (
                        "🔴"
                        if item["priority"] == "推奨"
                        else "🟡" if item["priority"] == "要注意（最近使用済み）" else "⚪"
                    )
                    formatted_lines.append(f"  {priority_emoji} {item['pesticide_name']} ({item['type']})")
                    formatted_lines.append(f"    希釈倍率: {item['dilution_rate']}")
                    formatted_lines.append(f"    対象病害虫: {', '.join(item['target_pests'])}")
                    formatted_lines.append(f"    収穫前日数: {item['days_before_harvest']}日")
                formatted_lines.append("")

            formatted_lines.append("💡 " + result.get("rotation_principle", ""))

        elif result_type == "weather_based":
            formatted_lines.append("🌤️ 天候を考慮した作業提案")
            formatted_lines.append("")

            for suggestion in result.get("suggestions", []):
                weather = suggestion["weather"]
                formatted_lines.append(f"📅 {suggestion['date']}")
                formatted_lines.append(f"🌡️ 天候: {weather['condition']}, 気温: {weather['temperature']}°C")
                formatted_lines.append(f"✅ 適した作業: {', '.join(suggestion['suitable_work'])}")
                if suggestion["avoid_work"]:
                    formatted_lines.append(f"❌ 避けるべき作業: {', '.join(suggestion['avoid_work'])}")
                formatted_lines.append(f"📝 {suggestion['notes']}")
                formatted_lines.append("")

            formatted_lines.append("💡 " + result.get("general_advice", ""))

        elif result_type == "weekly_work":
            formatted_lines.append("📅 来週の作業提案")
            formatted_lines.append(f"期間: {result.get('week_start')} - {result.get('week_end')}")
            formatted_lines.append("")

            for suggestion in result.get("suggestions", []):
                priority_emoji = (
                    "🔴"
                    if suggestion["priority"] == "high"
                    else "🟡" if suggestion["priority"] == "medium" else "⚪"
                )
                formatted_lines.append(
                    f"{priority_emoji} {suggestion['field_name']}: {suggestion['work_type']}"
                )
                formatted_lines.append(f"   理由: {suggestion['reason']}")
                formatted_lines.append(f"   予想時間: {suggestion['estimated_duration']}分")
                formatted_lines.append("")

        elif result_type == "crop_stage_based":
            formatted_lines.append("🌱 生育段階に応じた作業提案")
            formatted_lines.append("")

            for suggestion in result.get("suggestions", []):
                formatted_lines.append(f"📍 {suggestion['field_name']} ({suggestion['crop_name']})")
                formatted_lines.append(f"🌿 生育段階: {suggestion['growth_stage']}")
                formatted_lines.append("推奨作業:")

                for work in suggestion.get("recommended_work", []):
                    importance_emoji = (
                        "🔴" if work["importance"] == "高" else "🟡" if work["importance"] == "中" else "⚪"
                    )
                    formatted_lines.append(f"  {importance_emoji} {work['work']} (頻度: {work['frequency']})")
                formatted_lines.append("")

        elif result_type == "general_work":
            formatted_lines.append("📋 一般的な作業提案")
            formatted_lines.append(f"現在の月: {result.get('current_month')}月")
            formatted_lines.append("")

            for work in result.get("seasonal_work", []):
                priority_emoji = (
                    "🔴" if work["priority"] == "高" else "🟡" if work["priority"] == "中" else "⚪"
                )
                formatted_lines.append(f"{priority_emoji} {work['work']}")
                formatted_lines.append(f"   {work['note']}")
                formatted_lines.append("")

        return "\n".join(formatted_lines)

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期実行"""
        result = await self._execute(query)
        return self._format_result(result)
