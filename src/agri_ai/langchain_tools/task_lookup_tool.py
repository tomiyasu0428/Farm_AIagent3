"""
タスク検索ツール (T1: TaskLookupTool)
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List
from pydantic import Field
import logging

from .base_tool import AgriAIBaseTool

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
            # クエリの解析
            search_params = self._parse_query(query)
            
            # scheduled_tasksコレクションから検索
            scheduled_tasks_collection = await self._get_collection("scheduled_tasks")
            
            # 検索条件の構築
            filter_conditions = {"status": "pending"}
            
            # 日付範囲の設定
            if search_params.get("date_range"):
                filter_conditions["scheduled_date"] = search_params["date_range"]
            
            # 圃場指定の設定
            if search_params.get("field_filter"):
                filter_conditions["field_id"] = search_params["field_filter"]
            
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
                    "メモ": task.get("notes", "なし")
                }
                formatted_tasks.append(formatted_task)
            
            return formatted_tasks
            
        except Exception as e:
            logger.error(f"タスク検索エラー: {e}")
            return []
    
    def _parse_query(self, query: str) -> Dict[str, Any]:
        """クエリの解析"""
        params = {}
        
        # 今日のタスク
        if "今日" in query:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today + timedelta(days=1)
            params["date_range"] = {"$gte": today, "$lt": tomorrow}
        
        # 明日のタスク
        elif "明日" in query:
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            day_after_tomorrow = tomorrow + timedelta(days=1)
            params["date_range"] = {"$gte": tomorrow, "$lt": day_after_tomorrow}
        
        # 今週のタスク
        elif "今週" in query:
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            # 今週の日曜日を計算
            days_since_sunday = today.weekday() + 1 if today.weekday() != 6 else 0
            start_of_week = today - timedelta(days=days_since_sunday)
            end_of_week = start_of_week + timedelta(days=7)
            params["date_range"] = {"$gte": start_of_week, "$lt": end_of_week}
        
        # 圃場の指定
        field_keywords = ["A畑", "B畑", "C畑", "ハウス", "第1", "第2"]
        for keyword in field_keywords:
            if keyword in query:
                # 実際の実装では、圃場名からObjectIdを取得する必要があります
                # ここでは簡略化
                params["field_filter"] = {"$regex": keyword}
                break
        
        return params
    
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