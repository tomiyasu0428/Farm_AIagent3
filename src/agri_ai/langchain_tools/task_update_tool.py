"""
タスク更新ツール (T2: TaskUpdateTool)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from bson import ObjectId
import logging

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser

logger = logging.getLogger(__name__)


class TaskUpdateTool(AgriAIBaseTool):
    """タスクの更新・完了ツール"""
    
    name: str = "task_update"
    description: str = (
        "タスクの完了報告や更新を行います。"
        "使用例: '防除作業終わりました', 'A畑の灌水完了', 'タスクを延期します'"
    )
    
    async def _execute(self, query: str) -> Dict[str, Any]:
        """タスク更新の実行"""
        try:
            # クエリの解析
            parsed_query = query_parser.parse_comprehensive_query(query)
            action = self._determine_action(query)
            
            if action == "complete":
                return await self._complete_task(query, parsed_query)
            elif action == "postpone":
                return await self._postpone_task(query, parsed_query)
            elif action == "update":
                return await self._update_task(query, parsed_query)
            else:
                return {"error": "実行するアクションが特定できませんでした"}
                
        except Exception as e:
            logger.error(f"タスク更新エラー: {e}")
            return {"error": f"エラーが発生しました: {str(e)}"}
    
    def _determine_action(self, query: str) -> str:
        """クエリからアクションを決定"""
        complete_keywords = ["完了", "終わり", "終了", "できました", "やりました", "済み"]
        postpone_keywords = ["延期", "後回し", "明日", "来週", "遅らせる"]
        
        if any(keyword in query for keyword in complete_keywords):
            return "complete"
        elif any(keyword in query for keyword in postpone_keywords):
            return "postpone"
        else:
            return "update"
    
    async def _complete_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの完了処理"""
        try:
            # 該当するタスクを検索
            tasks = await self._find_matching_tasks(parsed_query)
            
            if not tasks:
                return {"message": "該当するタスクが見つかりませんでした"}
            
            # 複数タスクがある場合は最も適切なものを選択
            task_to_complete = self._select_best_match(tasks, parsed_query)
            
            # タスクを完了状態に更新
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            work_records_collection = await self._get_collection("work_records")
            
            # scheduled_tasksから削除
            await scheduled_tasks_collection.delete_one({"_id": task_to_complete["_id"]})
            
            # work_recordsに完了記録を追加
            work_record = {
                "field_id": task_to_complete["field_id"],
                "work_date": datetime.now(),
                "work_type": task_to_complete["work_type"],
                "worker": "LINE Bot User",  # 実際のユーザー情報は将来実装
                "materials_used": [],
                "work_details": {
                    "start_time": None,
                    "end_time": None,
                    "notes": f"LINE経由で完了報告: {query}"
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            
            # 次回作業の自動スケジュール
            next_work = await self._schedule_next_work(task_to_complete)
            if next_work:
                work_record["next_work_scheduled"] = next_work
            
            result = await work_records_collection.insert_one(work_record)
            
            # 圃場情報を取得
            field_info = await self._get_field_info(task_to_complete["field_id"])
            
            response = {
                "action": "completed",
                "task": {
                    "圃場": field_info.get("name", "不明"),
                    "作業内容": task_to_complete["work_type"],
                    "完了日": datetime.now().strftime("%Y-%m-%d %H:%M")
                },
                "message": f"【{field_info.get('name', '不明')}】の{task_to_complete['work_type']}が完了しました"
            }
            
            if next_work:
                response["next_work"] = {
                    "作業内容": next_work["work_type"],
                    "予定日": next_work["scheduled_date"].strftime("%Y-%m-%d")
                }
                response["message"] += f"\\n次回作業: {next_work['work_type']} ({next_work['scheduled_date'].strftime('%Y-%m-%d')})"
            
            return response
            
        except Exception as e:
            logger.error(f"タスク完了エラー: {e}")
            return {"error": f"タスク完了処理でエラーが発生しました: {str(e)}"}
    
    async def _postpone_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの延期処理"""
        try:
            # 該当するタスクを検索
            tasks = await self._find_matching_tasks(parsed_query)
            
            if not tasks:
                return {"message": "該当するタスクが見つかりませんでした"}
            
            # 延期日を決定
            postpone_date = self._determine_postpone_date(query)
            
            # タスクを更新
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            
            updated_tasks = []
            for task in tasks:
                await scheduled_tasks_collection.update_one(
                    {"_id": task["_id"]},
                    {
                        "$set": {
                            "scheduled_date": postpone_date,
                            "updated_at": datetime.now(),
                            "notes": f"延期: {query}"
                        }
                    }
                )
                
                field_info = await self._get_field_info(task["field_id"])
                updated_tasks.append({
                    "圃場": field_info.get("name", "不明"),
                    "作業内容": task["work_type"],
                    "新しい予定日": postpone_date.strftime("%Y-%m-%d")
                })
            
            return {
                "action": "postponed",
                "tasks": updated_tasks,
                "message": f"{len(updated_tasks)}件のタスクを{postpone_date.strftime('%Y-%m-%d')}に延期しました"
            }
            
        except Exception as e:
            logger.error(f"タスク延期エラー: {e}")
            return {"error": f"タスク延期処理でエラーが発生しました: {str(e)}"}
    
    async def _update_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの一般的な更新処理"""
        return {"message": "タスクの更新機能は今後実装予定です"}
    
    async def _find_matching_tasks(self, parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """条件に一致するタスクを検索"""
        try:
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            
            # 基本の検索条件
            filter_conditions = {"status": "pending"}
            
            # 日付条件
            date_component = parsed_query.get("parsed_components", {}).get("date")
            if date_component:
                filter_conditions["scheduled_date"] = date_component["date_range"]
            else:
                # 日付指定がない場合は今日から1週間以内のタスクを対象
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                filter_conditions["scheduled_date"] = {
                    "$gte": today,
                    "$lte": today + timedelta(days=7)
                }
            
            # 圃場条件
            field_component = parsed_query.get("parsed_components", {}).get("field")
            if field_component and field_component.get("field_filter"):
                field_ids = await self._get_field_ids_by_name(field_component["field_filter"])
                if field_ids:
                    filter_conditions["field_id"] = {"$in": field_ids}
            
            # 作業種別条件
            work_types = parsed_query.get("parsed_components", {}).get("work_types")
            if work_types:
                filter_conditions["work_type"] = {"$in": work_types}
            
            tasks = await scheduled_tasks_collection.find(filter_conditions).to_list(100)
            return tasks
            
        except Exception as e:
            logger.error(f"タスク検索エラー: {e}")
            return []
    
    async def _get_field_ids_by_name(self, field_filter: Dict[str, Any]) -> List[Any]:
        """圃場名から圃場IDを取得"""
        try:
            fields_collection = await self._get_collection("fields")
            fields = await fields_collection.find(field_filter, {"_id": 1}).to_list(100)
            return [field["_id"] for field in fields]
        except Exception as e:
            logger.error(f"圃場ID取得エラー: {e}")
            return []
    
    async def _get_field_info(self, field_id) -> Dict[str, Any]:
        """圃場情報の取得"""
        try:
            fields_collection = await self._get_collection("fields")
            field = await fields_collection.find_one({"_id": field_id})
            return field or {"name": "不明な圃場"}
        except Exception as e:
            logger.error(f"圃場情報取得エラー: {e}")
            return {"name": "不明な圃場"}
    
    def _select_best_match(self, tasks: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """最適なタスクを選択"""
        if len(tasks) == 1:
            return tasks[0]
        
        # 優先度で選択
        high_priority_tasks = [task for task in tasks if task.get("priority") == "high"]
        if high_priority_tasks:
            return high_priority_tasks[0]
        
        # 最も近い予定日のタスクを選択
        return min(tasks, key=lambda x: x["scheduled_date"])
    
    def _determine_postpone_date(self, query: str) -> datetime:
        """延期日を決定"""
        if "明日" in query:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif "来週" in query:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=7)
        elif "3日後" in query:
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=3)
        else:
            # デフォルトは明日
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    async def _schedule_next_work(self, completed_task: Dict[str, Any]) -> Dict[str, Any]:
        """次回作業の自動スケジュール"""
        try:
            # 防除作業の場合は7日後に次回防除をスケジュール
            if completed_task["work_type"] == "防除":
                next_date = datetime.now() + timedelta(days=7)
                
                # 次回タスクを作成
                scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
                next_task = {
                    "field_id": completed_task["field_id"],
                    "scheduled_date": next_date,
                    "work_type": "防除",
                    "priority": "medium",
                    "status": "pending",
                    "materials": [],
                    "notes": "前回防除作業の自動スケジュール",
                    "auto_generated": True,
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                
                await scheduled_tasks_collection.insert_one(next_task)
                
                return {
                    "work_type": "防除",
                    "scheduled_date": next_date,
                    "auto_generated": True
                }
            
            # 他の作業種別の場合は今後実装
            return None
            
        except Exception as e:
            logger.error(f"次回作業スケジュールエラー: {e}")
            return None
    
    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ {result['error']}"
        
        if result.get("action") == "completed":
            task = result.get("task", {})
            message = f"✅ {result.get('message', 'タスクが完了しました')}"
            
            if result.get("next_work"):
                next_work = result["next_work"]
                message += f"\\n\\n📋 次回予定: {next_work['作業内容']} ({next_work['予定日']})"
            
            return message
        
        elif result.get("action") == "postponed":
            return f"📅 {result.get('message', 'タスクを延期しました')}"
        
        else:
            return result.get("message", "処理が完了しました")