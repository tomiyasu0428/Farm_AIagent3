"""
作業提案ツール（修正版）
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from bson import ObjectId

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser

logger = logging.getLogger(__name__)


class WorkSuggestionTool(AgriAIBaseTool):
    """農業作業の提案を行うツール"""

    name: str = "work_suggestion"
    description: str = """農業作業の提案を行います。以下の用途で使用してください:
    - 作業計画: 「来週の作業計画を教えて」「トマトの次の作業は何？」
    - 農薬ローテーション: 「農薬のローテーション提案」「病害防除の計画」
    - 天候考慮: 「雨の日の作業」「晴れの日にできること」
    """

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期でツールを実行"""
        result = await self._execute(query)
        return self._format_result(result)

    async def _execute(self, query: str) -> Dict[str, Any]:
        """作業提案処理の実行"""
        try:
            # クエリを解析
            parsed_query = query_parser.parse_comprehensive_query(query)

            if self._is_rotation_query(query):
                return await self._suggest_pesticide_rotation(query, parsed_query)
            elif self._is_weather_query(query):
                return await self._suggest_weather_based_work(query, parsed_query)
            else:
                return await self._suggest_general_work(query, parsed_query)

        except Exception as e:
            logger.error(f"作業提案エラー: {e}")
            return {"error": f"処理中にエラーが発生しました: {str(e)}"}

    async def _suggest_general_work(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """一般的な作業提案"""
        async def db_operation(client):
            # 現在のタスクと圃場情報を取得
            tasks_collection = await client.get_collection("scheduled_tasks")
            fields_collection = await client.get_collection("fields")
            
            # 今後1週間のタスクを取得
            week_later = datetime.now() + timedelta(days=7)
            upcoming_tasks = await tasks_collection.find({
                "status": "pending",
                "scheduled_date": {"$lte": week_later}
            }).to_list(100)
            
            # 圃場情報を取得
            fields = await fields_collection.find({}).to_list(100)
            
            suggestions = []
            
            # 各圃場に対する提案を生成
            for field in fields:
                field_suggestions = await self._generate_field_suggestions(client, field)
                suggestions.extend(field_suggestions)
            
            return {
                "upcoming_tasks": upcoming_tasks,
                "suggestions": suggestions,
                "fields": fields
            }

        return await self._execute_with_db(db_operation)

    async def _generate_field_suggestions(self, client, field: Dict[str, Any]) -> List[Dict[str, Any]]:
        """個別圃場の作業提案を生成"""
        suggestions = []
        
        try:
            # 現在の作付け情報を取得
            current_cultivation = field.get("current_cultivation", {})
            if not current_cultivation:
                return suggestions
            
            crop_id = current_cultivation.get("crop_id")
            if not crop_id:
                return suggestions
            
            # 作物情報を取得
            crops_collection = await client.get_collection("crops")
            crop = await crops_collection.find_one({"_id": ObjectId(crop_id)})
            
            if not crop:
                return suggestions
            
            # 生育段階に基づく作業提案
            growth_stage = current_cultivation.get("growth_stage", "不明")
            planting_date = current_cultivation.get("planting_date", datetime.now())
            
            # 日数計算
            days_since_planting = (datetime.now() - planting_date).days
            
            # 作業提案の生成
            if growth_stage == "開花期":
                suggestions.append({
                    "field_name": field.get("name", "不明"),
                    "crop_name": crop.get("name", "不明"),
                    "suggestion": "開花期の管理",
                    "details": "受粉促進、温度管理、適切な水やり",
                    "priority": "high",
                    "recommended_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                })
            elif growth_stage == "結実期":
                suggestions.append({
                    "field_name": field.get("name", "不明"),
                    "crop_name": crop.get("name", "不明"),
                    "suggestion": "結実期の管理",
                    "details": "追肥、支柱の設置、病害虫防除",
                    "priority": "medium",
                    "recommended_date": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
                })
            
            # 定期的な防除提案
            if days_since_planting % 14 == 0:  # 2週間ごと
                suggestions.append({
                    "field_name": field.get("name", "不明"),
                    "crop_name": crop.get("name", "不明"),
                    "suggestion": "定期防除",
                    "details": "病害虫の予防散布",
                    "priority": "medium",
                    "recommended_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
                })
            
        except Exception as e:
            logger.error(f"圃場提案生成エラー: {e}")
        
        return suggestions

    async def _suggest_pesticide_rotation(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """農薬ローテーション提案"""
        async def db_operation(client):
            materials_collection = await client.get_collection("materials")
            
            # 殺菌剤を取得
            fungicides = await materials_collection.find({
                "type": "殺菌剤"
            }).to_list(100)
            
            # 殺虫剤を取得
            insecticides = await materials_collection.find({
                "type": "殺虫剤"
            }).to_list(100)
            
            # ローテーション提案を生成
            rotation_plan = []
            
            # 殺菌剤ローテーション
            if len(fungicides) >= 2:
                rotation_plan.append({
                    "week": 1,
                    "type": "殺菌剤",
                    "material": fungicides[0].get("name", "不明"),
                    "purpose": "病害予防"
                })
                rotation_plan.append({
                    "week": 3,
                    "type": "殺菌剤",
                    "material": fungicides[1].get("name", "不明"),
                    "purpose": "病害予防（抵抗性対策）"
                })
            
            # 殺虫剤ローテーション
            if len(insecticides) >= 2:
                rotation_plan.append({
                    "week": 2,
                    "type": "殺虫剤",
                    "material": insecticides[0].get("name", "不明"),
                    "purpose": "害虫防除"
                })
                rotation_plan.append({
                    "week": 4,
                    "type": "殺虫剤",
                    "material": insecticides[1].get("name", "不明"),
                    "purpose": "害虫防除（抵抗性対策）"
                })
            
            return {
                "rotation_plan": rotation_plan,
                "available_fungicides": len(fungicides),
                "available_insecticides": len(insecticides)
            }

        return await self._execute_with_db(db_operation)

    async def _suggest_weather_based_work(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """天候に基づく作業提案"""
        # 簡易的な天候別作業提案
        if "雨" in query:
            return {
                "weather_condition": "雨天",
                "suitable_works": [
                    {"work": "ハウス内作業", "details": "温度・湿度管理、整枝・誘引"},
                    {"work": "資材整理", "details": "農薬・肥料の在庫確認"},
                    {"work": "記録整理", "details": "作業記録の入力・整理"},
                ],
                "avoid_works": [
                    {"work": "散布作業", "reason": "雨で農薬が流れる"},
                    {"work": "収穫作業", "reason": "品質低下のリスク"},
                ]
            }
        elif "晴れ" in query:
            return {
                "weather_condition": "晴天",
                "suitable_works": [
                    {"work": "散布作業", "details": "病害虫防除、葉面散布"},
                    {"work": "収穫作業", "details": "品質の良い時期での収穫"},
                    {"work": "圃場作業", "details": "耕起、畝立て、定植"},
                ],
                "avoid_works": [
                    {"work": "高温時の重労働", "reason": "熱中症のリスク"},
                ]
            }
        else:
            return {
                "weather_condition": "一般",
                "suitable_works": [
                    {"work": "日常管理", "details": "観察、水やり、整枝"},
                    {"work": "計画作業", "details": "スケジュール確認、準備"},
                ]
            }

    def _is_rotation_query(self, query: str) -> bool:
        """ローテーションクエリかどうかを判定"""
        rotation_keywords = ["ローテーション", "農薬", "防除", "散布", "計画"]
        return any(keyword in query for keyword in rotation_keywords)

    def _is_weather_query(self, query: str) -> bool:
        """天候クエリかどうかを判定"""
        weather_keywords = ["雨", "晴れ", "天気", "天候", "曇り"]
        return any(keyword in query for keyword in weather_keywords)

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ エラー: {result['error']}"

        # ローテーション提案の場合
        if "rotation_plan" in result:
            plan_text = "🔄 農薬ローテーション提案\n\n"
            for item in result["rotation_plan"]:
                plan_text += f"第{item['week']}週: {item['material']} ({item['type']})\n"
                plan_text += f"  目的: {item['purpose']}\n\n"
            return plan_text

        # 天候別作業提案の場合
        if "weather_condition" in result:
            weather_text = f"🌤️ {result['weather_condition']}時の作業提案\n\n"
            
            if "suitable_works" in result:
                weather_text += "✅ 適している作業:\n"
                for work in result["suitable_works"]:
                    weather_text += f"• {work['work']}: {work['details']}\n"
                weather_text += "\n"
            
            if "avoid_works" in result:
                weather_text += "❌ 避けるべき作業:\n"
                for work in result["avoid_works"]:
                    weather_text += f"• {work['work']}: {work['reason']}\n"
            
            return weather_text

        # 一般的な作業提案の場合
        if "suggestions" in result:
            suggestion_text = "💡 作業提案\n\n"
            
            for suggestion in result["suggestions"]:
                priority_emoji = "🔴" if suggestion["priority"] == "high" else "🟡"
                suggestion_text += f"{priority_emoji} {suggestion['field_name']} ({suggestion['crop_name']})\n"
                suggestion_text += f"   {suggestion['suggestion']}: {suggestion['details']}\n"
                suggestion_text += f"   推奨日: {suggestion['recommended_date']}\n\n"
            
            return suggestion_text if suggestion_text != "💡 作業提案\n\n" else "現在、特別な作業提案はありません。"

        return "✅ 作業提案を確認しました。"