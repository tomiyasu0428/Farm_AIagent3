import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime
from src.agri_ai.core.master_agent import MasterAgent
from src.agri_ai.database.mongodb_client import MongoDBClient

@pytest.fixture(scope="module")
def master_agent_instance():
    # MasterAgentのインスタンスを生成
    agent = MasterAgent()
    # MongoDBClientのモックを設定
    with patch('src.agri_ai.database.mongodb_client.MongoDBClient') as MockMongoDBClient:
        mock_client = MockMongoDBClient.return_value
        mock_client.is_connected = True
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        mock_collection = AsyncMock()
        mock_client.get_collection.return_value = mock_collection
        
        # DataAccessLayerのsearch_work_logsをモック
        with patch('src.agri_ai.database.data_access.DataAccessLayer.search_work_logs') as mock_search_work_logs:
            # テストデータ
            mock_search_work_logs.return_value = [
                {
                    "log_id": "log_1",
                    "work_date": datetime(2025, 7, 23),
                    "category": "収穫",
                    "original_message": "トマトハウスでトマトを10kg収穫しました。",
                    "extracted_data": {"field_name": "トマトハウス", "crop_name": "トマト", "work_content": "収穫", "quantity": "10kg"},
                    "created_at": datetime(2025, 7, 23, 10, 0)
                },
                {
                    "log_id": "log_2",
                    "work_date": datetime(2025, 7, 22),
                    "category": "防除",
                    "original_message": "第2圃場でピーマンに農薬を散布しました。",
                    "extracted_data": {"field_name": "第2圃場", "crop_name": "ピーマン", "work_content": "農薬散布", "material_names": ["モスピラン"]},
                    "created_at": datetime(2025, 7, 22, 14, 30)
                }
            ]
            
            # エージェントの初期化
            agent.initialize()
            yield agent

@pytest.mark.asyncio
async def test_work_log_search_integration(master_agent_instance):
    user_id = "test_user_123"
    query = "昨日の作業記録を教えて"
    
    response = await master_agent_instance.process_message_async(query, user_id)
    
    assert response['response'] is not None
    assert "作業記録が見つかりました (2件)" in response['response']
    assert "日付: 2025-07-23 圃場: トマトハウス 作業内容: 収穫" in response['response']
    assert "日付: 2025-07-22 圃場: 第2圃場 作業内容: 農薬散布" in response['response']
    assert response['agent_used'] == 'master_agent'

@pytest.mark.asyncio
async def test_work_log_search_no_results(master_agent_instance):
    user_id = "test_user_123"
    query = "2000年の作業記録を教えて"
    
    # search_work_logsが空のリストを返すようにモックを設定
    with patch('src.agri_ai.database.data_access.DataAccessLayer.search_work_logs') as mock_search_work_logs:
        mock_search_work_logs.return_value = []
        response = await master_agent_instance.process_message_async(query, user_id)
    
    assert response['response'] is not None
    assert "該当する作業記録は見つかりませんでした。" in response['response']
    assert response['agent_used'] == 'master_agent'
