"""
タスク更新ツール (T2: TaskUpdateTool)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
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
            logger.error(f"タスク更新エラー: {e}", exc_info=True)
            return {"error": f"エラーが発生しました: {str(e)}"}

    def _determine_action(self, query: str) -> str:
        """クエリからアクションを決定"""
        complete_keywords = ["完了", "終わり", "終了", "できました", "やりました", "済み"]
        postpone_keywords = ["延期", "後回し", "明日", "来週", "遅らせる"]
        # update_keywords = ["更新", "変更", "修正"] # 将来的に使用

        if any(keyword in query for keyword in complete_keywords):
            return "complete"
        elif any(keyword in query for keyword in postpone_keywords):
            return "postpone"
        else:
            # デフォルトは完了とみなすことが多いので、より明確なキーワードがない場合は更新とする
            return "update"

    async def _complete_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの完了処理"""
        try:
            # 該当するタスクを検索
            tasks = await self._find_matching_tasks(parsed_query)

            if not tasks:
                return {"message": "該当する未完了タスクが見つかりませんでした。"}

            # 複数タスクがある場合は最も適切なものを選択
            task_to_complete = self._select_best_match(tasks, parsed_query)
            if not task_to_complete:
                return {"message": "完了対象のタスクを特定できませんでした。"}

            # データベース操作を新しい接続で実行
            async def db_operation(client):
                scheduled_tasks_collection = await client.get_collection("scheduled_tasks")
                work_records_collection = await client.get_collection("work_records")

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
                return True

            await self._execute_with_db(db_operation)

            next_work = await self._schedule_next_work(task_to_complete)
            if next_work:
                work_record["next_work_scheduled"] = next_work

            await work_records_collection.insert_one(work_record)

            # 圃場情報を取得
            field_info = await self._get_field_info(task_to_complete.get("field_id"))

            response = {
                "action": "completed",
                "task": {
                    "圃場": field_info.get("name", "不明"),
                    "作業内容": task_to_complete["work_type"],
                    "完了日": datetime.now().strftime("%Y-%m-%d %H:%M"),
                },
            }

            message = (
                f"✅ 【{field_info.get('name', '不明')}】の {task_to_complete['work_type']} を完了しました。"
            )

            if next_work:
                response["next_work"] = {
                    "作業内容": next_work["work_type"],
                    "予定日": next_work["scheduled_date"].strftime("%Y-%m-%d"),
                }
                message += f"\n次の作業として {next_work['work_type']} を {next_work['scheduled_date'].strftime('%Y-%m-%d')} に予定しました。"

            response["message"] = message
            return response

        except Exception as e:
            logger.error(f"タスク完了エラー: {e}", exc_info=True)
            return {"error": f"タスク完了処理でエラーが発生しました: {str(e)}"}

    async def _postpone_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの延期処理"""
        try:
            # 該当するタスクを検索
            tasks = await self._find_matching_tasks(parsed_query)

            if not tasks:
                return {"message": "延期対象のタスクが見つかりませんでした。"}

            # 延期日を決定
            postpone_date = self._determine_postpone_date(query)
            if not postpone_date:
                return {"error": "延期日を特定できませんでした。"}

            # タスクを更新
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")

            updated_tasks_info = []
            for task in tasks:
                await scheduled_tasks_collection.update_one(
                    {"_id": task["_id"]},
                    {
                        "$set": {
                            "scheduled_date": postpone_date,
                            "updated_at": datetime.now(),
                            "notes": f"({datetime.now().strftime('%Y-%m-%d')})延期: {query}",
                        }
                    },
                )

                field_info = await self._get_field_info(task.get("field_id"))
                updated_tasks_info.append(
                    {
                        "圃場": field_info.get("name", "不明"),
                        "作業内容": task["work_type"],
                        "新しい予定日": postpone_date.strftime("%Y-%m-%d"),
                    }
                )

            return {
                "action": "postponed",
                "tasks": updated_tasks_info,
                "message": f"✅ {len(updated_tasks_info)}件のタスクを{postpone_date.strftime('%Y-%m-%d')}に延期しました。",
            }

        except Exception as e:
            logger.error(f"タスク延期エラー: {e}", exc_info=True)
            return {"error": f"タスク延期処理でエラーが発生しました: {str(e)}"}

    async def _update_task(self, query: str, parsed_query: Dict[str, Any]) -> Dict[str, Any]:
        """タスクの一般的な更新処理"""
        # 今は完了と見なして処理を試みる
        return await self._complete_task(query, parsed_query)

    async def _find_matching_tasks(self, parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """条件に一致するタスクを検索"""
        try:
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            filter_conditions: Dict[str, Any] = {"status": "pending"}

            date_component = parsed_query.get("parsed_components", {}).get("date")
            if date_component:
                filter_conditions["scheduled_date"] = date_component["date_range"]
            else:
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                filter_conditions["scheduled_date"] = {
                    "$gte": today - timedelta(days=7),
                    "$lte": today + timedelta(days=1),
                }

            field_component = parsed_query.get("parsed_components", {}).get("field")
            if field_component and field_component.get("field_filter"):
                field_ids = await self._get_field_ids_by_name(field_component["field_filter"])
                if field_ids:
                    filter_conditions["field_id"] = {"$in": field_ids}

            work_types = parsed_query.get("parsed_components", {}).get("work_types")
            if work_types:
                filter_conditions["work_type"] = {"$in": work_types}

            tasks = (
                await scheduled_tasks_collection.find(filter_conditions)
                .sort("scheduled_date", 1)
                .to_list(100)
            )
            return tasks
        except Exception as e:
            logger.error(f"タスク検索エラー: {e}", exc_info=True)
            return []

    async def _get_field_ids_by_name(self, field_filter: Dict[str, Any]) -> List[Any]:
        """圃場名から圃場IDを取得"""
        try:
            fields_collection = await self._get_collection("fields")
            fields = await fields_collection.find(field_filter, {"_id": 1}).to_list(100)
            return [field["_id"] for field in fields]
        except Exception as e:
            logger.error(f"圃場ID取得エラー: {e}", exc_info=True)
            return []

    async def _get_field_info(self, field_id: Optional[Any]) -> Dict[str, Any]:
        """圃場情報の取得"""
        if not field_id:
            return {"name": "不明な圃場"}
        try:
            fields_collection = await self._get_collection("fields")
            field = await fields_collection.find_one({"_id": field_id})
            return field or {"name": "不明な圃場"}
        except Exception as e:
            logger.error(f"圃場情報取得エラー: {e}", exc_info=True)
            return {"name": "不明な圃場"}

    def _select_best_match(
        self, tasks: List[Dict[str, Any]], parsed_query: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """最適なタスクを選択"""
        if not tasks:
            return None
        if len(tasks) == 1:
            return tasks[0]

        # 今日が予定日のタスクを優先
        today = datetime.now().date()
        today_tasks = [t for t in tasks if t.get("scheduled_date", datetime.min).date() == today]
        if len(today_tasks) == 1:
            return today_tasks[0]
        if len(today_tasks) > 1:
            tasks = today_tasks

        # 優先度で選択
        high_priority_tasks = [task for task in tasks if task.get("priority") == "high"]
        if high_priority_tasks:
            return high_priority_tasks[0]

        # 最も近い過去のタスクを選択
        return min(
            tasks, key=lambda x: abs((x.get("scheduled_date", datetime.min) - datetime.now()).total_seconds())
        )

    def _determine_postpone_date(self, query: str) -> Optional[datetime]:
        """延期日を決定"""
        date_info = query_parser.parse_date_query(query)
        if date_info and isinstance(date_info.get("date_range", {}).get("$gte"), datetime):
            return date_info["date_range"]["$gte"]

        if "明日" in query:
            return datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        if "明後日" in query:
            return datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=2)
        if "来週" in query:
            return datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=7)

        return None

    async def _schedule_next_work(self, completed_task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """次回作業のスケジュール"""
        if completed_task.get("work_type") == "防除":
            next_work_date = datetime.now() + timedelta(days=7)
            next_work = {
                "field_id": completed_task["field_id"],
                "work_type": "防除",
                "scheduled_date": next_work_date,
                "priority": "medium",
                "status": "pending",
                "notes": "前回の防除から7日後に自動スケジュール",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            await scheduled_tasks_collection.insert_one(next_work)
            return next_work
        return None

    def _format_result(self, result: Dict[str, Any]) -> str:
        """結果のフォーマット"""
        if not result or result.get("error"):
            return f"❌ {result.get('error', '不明なエラー')}"

        return result.get("message", "処理が完了しました。")

    async def _arun(self, query: str, **kwargs: Any) -> str:
        """非同期実行"""
        result = await self._execute(query)
        return self._format_result(result)
