"""
タスク検索ツール (T1: TaskLookupTool)
"""

from typing import Any, Dict, List
import logging

from .base_tool import AgriAIBaseTool
from ..utils.query_parser import query_parser

logger = logging.getLogger(__name__)


class TaskLookupTool(AgriAIBaseTool):
    """未完了タスクの検索ツール"""

    name: str = "task_lookup"
    description: str = (
        "今日のタスクや指定した日付のタスクを検索します。"
        "使用例: '今日のタスク', '明日の作業予定', 'A畑の今週のタスク'"
    )

    async def _execute(self, query: str) -> List[Dict[str, Any]]:
        """タスク検索の実行"""
        try:
            # 改良されたクエリ解析を使用
            parsed_query = query_parser.parse_comprehensive_query(query)

            # scheduled_tasksコレクションから検索
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")

            # 検索条件の構築
            filter_conditions: Dict[str, Any] = {"status": "pending"}

            # 日付範囲の設定
            date_component = parsed_query.get("parsed_components", {}).get("date")
            if date_component:
                filter_conditions["scheduled_date"] = date_component["date_range"]

            # 圃場指定の設定
            field_component = parsed_query.get("parsed_components", {}).get("field")
            if field_component:
                if field_component.get("all_fields"):
                    # 全圃場の場合は特別な処理は不要
                    pass
                elif field_component.get("field_filter"):
                    # 圃場名での検索の場合、まず圃場IDを取得
                    field_ids = await self._get_field_ids_by_name(field_component["field_filter"])
                    if field_ids:
                        filter_conditions["field_id"] = {"$in": field_ids}
                    else:
                        # 該当する圃場がない場合
                        return []

            # 作業種別の設定
            work_types = parsed_query.get("parsed_components", {}).get("work_types")
            if work_types:
                filter_conditions["work_type"] = {"$in": work_types}

            # 優先度の設定
            priority = parsed_query.get("parsed_components", {}).get("priority")
            if priority:
                filter_conditions["priority"] = priority

            # タスクの検索
            tasks = await scheduled_tasks_collection.find(filter_conditions).to_list(100)

            # 結果の整形
            formatted_tasks = []
            for task in tasks:
                # 圃場情報の取得
                field_info = await self._get_field_info(task["field_id"])

                formatted_task = {
                    "圃場": field_info.get("name", "不明"),
                    "作業内容": task["work_type"],
                    "予定日": task["scheduled_date"].strftime("%Y-%m-%d"),
                    "優先度": task["priority"],
                    "メモ": task.get("notes", "なし"),
                }
                formatted_tasks.append(formatted_task)

            return formatted_tasks

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

    def _format_result(self, result: List[Dict[str, Any]]) -> str:
        """結果のフォーマット"""
        if not result:
            return "該当するタスクがありません。"

        formatted_lines = [f"📋 {len(result)}件のタスクが見つかりました:\n"]

        for i, task in enumerate(result, 1):
            task_line = (
                f"{i}. 【{task['圃場']}】{task['作業内容']}\n"
                f"   📅 {task['予定日']} (優先度: {task['優先度']})\n"
                f"   📝 {task['メモ']}\n"
            )
            formatted_lines.append(task_line)

        return "\n".join(formatted_lines)

    async def _arun(self, query: str, run_manager: Any = None) -> str:
        """非同期実行"""
        try:
            result = await self._execute(query)
            return self._format_result(result)
        except Exception as e:
            logger.error(f"タスク検索エラー: {e}")
            return f"タスク検索でエラーが発生しました: {str(e)}"
