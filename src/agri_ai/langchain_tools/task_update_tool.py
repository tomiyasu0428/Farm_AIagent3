"""
作業タスク更新ツール（修正版）
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from bson import ObjectId

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser

logger = logging.getLogger(__name__)


class TaskUpdateTool(AgriAIBaseTool):
    """作業タスクの更新・完了処理を行うツール"""

    name: str = "task_update"
    description: str = """作業タスクの更新・完了報告を処理します。以下の形式で使用してください:
    - 作業完了: 「防除作業が完了しました」「第1ハウスの水やり終了」
    - タスク延期: 「明日の防除を来週に延期」「トマトの収穫を3日後に変更」
    """

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期でツールを実行"""
        result = await self._execute(query)
        return self._format_result(result)

    async def _execute(self, query: str) -> Dict[str, Any]:
        """タスク更新処理の実行"""
        try:
            # クエリを解析して意図を判定
            parsed_query = query_parser.parse_comprehensive_query(query)
            
            if self._is_completion_query(query):
                return await self._handle_task_completion(query, parsed_query)
            elif self._is_postpone_query(query):
                return await self._handle_task_postpone(query, parsed_query)
            else:
                return {"error": "更新内容を特定できませんでした。"}

        except Exception as e:
            logger.error(f"タスク更新エラー: {e}")
            return {"error": f"処理中にエラーが発生しました: {str(e)}"}

    async def _handle_task_completion(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスク完了処理"""
        async def db_operation(client):
            # 該当するタスクを検索
            scheduled_tasks_collection = await client.get_collection("scheduled_tasks")
            work_records_collection = await client.get_collection("work_records")
            
            # 検索条件を構築
            filter_conditions = {"status": "pending"}
            
            # 作業種別の抽出
            work_types = parsed_query.get("parsed_components", {}).get("work_types", [])
            if work_types:
                filter_conditions["work_type"] = {"$in": work_types}
            
            # 圃場の抽出
            field_component = parsed_query.get("parsed_components", {}).get("field")
            if field_component and field_component.get("field_filter"):
                fields_collection = await client.get_collection("fields")
                matching_fields = await fields_collection.find(
                    {"name": {"$regex": field_component["field_filter"], "$options": "i"}}
                ).to_list(100)
                if matching_fields:
                    field_ids = [field["_id"] for field in matching_fields]
                    filter_conditions["field_id"] = {"$in": field_ids}
            
            tasks = await scheduled_tasks_collection.find(filter_conditions).to_list(100)
            
            if not tasks:
                return {"message": "完了対象のタスクが見つかりませんでした。"}
            
            # 最も適切なタスクを選択
            task_to_complete = self._select_best_match(tasks, parsed_query)
            if not task_to_complete:
                return {"message": "完了対象のタスクを特定できませんでした。"}
            
            # scheduled_tasksから削除
            await scheduled_tasks_collection.delete_one({"_id": task_to_complete["_id"]})
            
            # work_recordsに完了記録を追加
            work_record = {
                "field_id": task_to_complete["field_id"],
                "work_date": datetime.now(),
                "work_type": task_to_complete["work_type"],
                "worker": "LINE Bot User",
                "materials_used": [],
                "work_details": {
                    "notes": f"LINE経由で完了報告: {query}",
                },
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            await work_records_collection.insert_one(work_record)
            
            return {
                "message": f"タスク「{task_to_complete['work_type']}」を完了として記録しました。",
                "completed_task": task_to_complete,
                "work_record": work_record
            }

        return await self._execute_with_db(db_operation)

    async def _handle_task_postpone(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスク延期処理"""
        async def db_operation(client):
            scheduled_tasks_collection = await client.get_collection("scheduled_tasks")
            
            # 延期対象のタスクを検索
            filter_conditions = {"status": "pending"}
            
            # 延期日の抽出
            date_component = parsed_query.get("parsed_components", {}).get("date")
            postpone_date = None
            if date_component:
                postpone_date = date_component.get("date_range", {}).get("$gte")
            
            if not postpone_date:
                return {"error": "延期日を特定できませんでした。"}
            
            # 作業種別の抽出
            work_types = parsed_query.get("parsed_components", {}).get("work_types", [])
            if work_types:
                filter_conditions["work_type"] = {"$in": work_types}
            
            tasks = await scheduled_tasks_collection.find(filter_conditions).to_list(100)
            
            if not tasks:
                return {"message": "延期対象のタスクが見つかりませんでした。"}
            
            # タスクを更新
            updated_tasks_info = []
            for task in tasks:
                await scheduled_tasks_collection.update_one(
                    {"_id": task["_id"]},
                    {
                        "$set": {
                            "scheduled_date": postpone_date,
                            "updated_at": datetime.now(),
                            "postpone_reason": f"LINE経由で延期: {query}"
                        }
                    }
                )
                
                updated_tasks_info.append({
                    "task_id": str(task["_id"]),
                    "work_type": task["work_type"],
                    "new_date": postpone_date.strftime("%Y-%m-%d"),
                })
            
            return {
                "message": f"{len(updated_tasks_info)}件のタスクを延期しました。",
                "updated_tasks": updated_tasks_info
            }

        return await self._execute_with_db(db_operation)

    def _is_completion_query(self, query: str) -> bool:
        """完了クエリかどうかを判定"""
        completion_keywords = ["完了", "終了", "終わり", "済み", "できました", "やりました"]
        return any(keyword in query for keyword in completion_keywords)

    def _is_postpone_query(self, query: str) -> bool:
        """延期クエリかどうかを判定"""
        postpone_keywords = ["延期", "変更", "遅らせ", "後回し", "来週", "明日", "後で"]
        return any(keyword in query for keyword in postpone_keywords)

    def _select_best_match(self, tasks: List[Dict[str, Any]], parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """最適なタスクを選択"""
        if len(tasks) == 1:
            return tasks[0]
        
        # 日付が近いタスクを優先
        today = datetime.now().date()
        for task in tasks:
            task_date = task.get("scheduled_date", datetime.now()).date()
            if abs((task_date - today).days) <= 1:  # 今日または明日のタスク
                return task
        
        # 優先度が高いタスクを選択
        for priority in ["high", "medium", "low"]:
            for task in tasks:
                if task.get("priority") == priority:
                    return task
        
        return tasks[0] if tasks else None

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if result.get("error"):
            return f"❌ エラー: {result['error']}"
        
        message = result.get("message", "処理が完了しました。")
        
        if "completed_task" in result:
            task = result["completed_task"]
            return f"✅ {message}\n📋 完了タスク: {task['work_type']}"
        
        if "updated_tasks" in result:
            tasks_info = "\n".join([
                f"  • {task['work_type']} → {task['new_date']}"
                for task in result["updated_tasks"]
            ])
            return f"📅 {message}\n{tasks_info}"
        
        return f"✅ {message}"