"""
LangChainツールの単体テスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from src.agri_ai.langchain_tools.task_lookup_tool import TaskLookupTool
from src.agri_ai.langchain_tools.field_info_tool import FieldInfoTool


class TestTaskLookupTool:
    """TaskLookupToolのテストクラス"""
    
    @pytest.fixture
    def tool(self):
        """テスト用ツールの作成"""
        tool = TaskLookupTool()
        tool.mongodb_client = MagicMock()
        return tool
    
    @pytest.mark.asyncio
    async def test_execute_today_tasks(self, tool):
        """今日のタスク検索テスト"""
        # モックデータ
        mock_tasks = [
            {
                "field_id": "test_field_id",
                "work_type": "防除",
                "scheduled_date": datetime.now(),
                "priority": "high",
                "notes": "テストメモ"
            }
        ]
        
        # モック設定
        mock_collection = AsyncMock()
        mock_collection.find.return_value.to_list = AsyncMock(return_value=mock_tasks)
        tool._get_collection = AsyncMock(return_value=mock_collection)
        tool._get_field_info = AsyncMock(return_value={"name": "テスト圃場"})
        
        # テスト実行
        result = await tool._execute("今日のタスク")
        
        # 結果検証
        assert len(result) == 1
        assert result[0]["作業内容"] == "防除"
        assert result[0]["圃場"] == "テスト圃場"
    
    @pytest.mark.asyncio
    async def test_parse_query_today(self, tool):
        """クエリ解析テスト（今日）"""
        params = tool._parse_query("今日のタスク")
        assert "date_range" in params
        assert "$gte" in params["date_range"]
        assert "$lt" in params["date_range"]
    
    @pytest.mark.asyncio
    async def test_parse_query_field_filter(self, tool):
        """クエリ解析テスト（圃場フィルタ）"""
        params = tool._parse_query("A畑のタスク")
        assert "field_filter" in params
        assert "$regex" in params["field_filter"]


class TestFieldInfoTool:
    """FieldInfoToolのテストクラス"""
    
    @pytest.fixture
    def tool(self):
        """テスト用ツールの作成"""
        tool = FieldInfoTool()
        tool.mongodb_client = MagicMock()
        return tool
    
    @pytest.mark.asyncio
    async def test_execute_single_field(self, tool):
        """単一圃場情報取得テスト"""
        # モックデータ
        mock_field = {
            "field_code": "A-01",
            "name": "第1ハウス",
            "area": 300,
            "soil_type": "砂壌土",
            "current_cultivation": {
                "crop_id": "test_crop_id",
                "variety": "桃太郎",
                "planting_date": "2024-03-15",
                "growth_stage": "開花期"
            },
            "next_scheduled_work": {
                "work_type": "防除",
                "scheduled_date": "2024-07-17"
            }
        }
        
        # モック設定
        mock_collection = AsyncMock()
        mock_collection.find_one = AsyncMock(return_value=mock_field)
        tool._get_collection = AsyncMock(return_value=mock_collection)
        tool._get_crop_info = AsyncMock(return_value={"name": "トマト"})
        
        # テスト実行
        result = await tool._execute("第1ハウスの状況")
        
        # 結果検証
        assert "圃場情報" in result
        assert result["圃場情報"]["圃場名"] == "第1ハウス"
        assert "現在の作付け" in result
        assert result["現在の作付け"]["作物"] == "トマト"
    
    @pytest.mark.asyncio
    async def test_parse_field_query_all(self, tool):
        """クエリ解析テスト（全圃場）"""
        filter_params = tool._parse_field_query("全圃場の状況")
        assert filter_params["all_fields"] is True
    
    @pytest.mark.asyncio
    async def test_parse_field_query_specific(self, tool):
        """クエリ解析テスト（特定圃場）"""
        filter_params = tool._parse_field_query("A畑の状況")
        assert "$or" in filter_params
        assert any("$regex" in condition for condition in filter_params["$or"])