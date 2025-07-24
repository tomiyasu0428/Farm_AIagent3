import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from src.agri_ai.agents.work_log_search_agent import WorkLogSearchAgent

@pytest.fixture
def mock_data_access():
    with patch('src.agri_ai.agents.work_log_search_agent.DataAccessLayer') as MockDataAccessLayer:
        mock_instance = MockDataAccessLayer.return_value
        mock_instance.search_work_logs = AsyncMock()
        yield mock_instance

@pytest.fixture
def work_log_search_agent(mock_data_access):
    agent = WorkLogSearchAgent()
    agent.data_access = mock_data_access # MockDataAccessLayerのインスタンスを注入
    return agent

@pytest.mark.asyncio
async def test_parse_search_query_yesterday(work_log_search_agent):
    query = "昨日の作業記録を教えて"
    params = await work_log_search_agent._parse_search_query(query)
    assert 'date_range' in params
    assert 'start' in params['date_range']
    assert 'end' in params['date_range']
    assert params['date_range']['start'].day == (datetime.now() - timedelta(days=1)).day

@pytest.mark.asyncio
async def test_parse_search_query_last_month(work_log_search_agent):
    query = "先月の防除記録を教えて"
    params = await work_log_search_agent._parse_search_query(query)
    assert 'date_range' in params
    assert 'start' in params['date_range']
    assert 'end' in params['date_range']
    assert params['date_range']['start'].month == (datetime.now().replace(day=1) - timedelta(days=1)).month
    assert '防除' in params['work_categories']

@pytest.mark.asyncio
async def test_parse_search_query_field_and_crop(work_log_search_agent):
    query = "トマトハウスのトマトの収穫記録"
    params = await work_log_search_agent._parse_search_query(query)
    assert 'トマトハウス' in params['field_names']
    assert 'トマト' in params['crop_names']
    assert '収穫' in params['work_categories']

@pytest.mark.asyncio
async def test_execute_search(work_log_search_agent, mock_data_access):
    mock_data_access.search_work_logs.return_value = [
        {"work_date": datetime.now(), "category": "収穫", "original_message": "トマト収穫", "extracted_data": {"field_name": "トマトハウス"}}
    ]
    params = {"field_names": ["トマトハウス"], "user_id": "test_user"}
    results = await work_log_search_agent._execute_search(params, "test_user")
    assert len(results) == 1
    mock_data_access.search_work_logs.assert_called_once_with(params, "test_user")

@pytest.mark.asyncio
async def test_analyze_results_empty(work_log_search_agent):
    results = []
    analyzed = await work_log_search_agent._analyze_results(results, {})
    assert analyzed['total_count'] == 0
    assert "該当する作業記録が見つかりませんでした" in analyzed['recommendations'][0]

@pytest.mark.asyncio
async def test_analyze_results_with_data(work_log_search_agent):
    mock_results = [
        {"work_date": datetime(2025, 7, 20), "category": "防除", "original_message": "防除作業", "extracted_data": {"field_name": "第1ハウス", "material_names": ["ダコニール"]}},
        {"work_date": datetime(2025, 7, 22), "category": "施肥", "original_message": "施肥作業", "extracted_data": {"field_name": "第1ハウス"}},
        {"work_date": datetime(2025, 7, 23), "category": "防除", "original_message": "防除作業", "extracted_data": {"field_name": "第2ハウス", "material_names": ["アブラムシコロリ"]}}
    ]
    analyzed = await work_log_search_agent._analyze_results(mock_results, {})
    assert analyzed['total_count'] == 3
    assert analyzed['statistics']['work_categories']['防除'] == 2
    assert analyzed['statistics']['fields']['第1ハウス'] == 2

@pytest.mark.asyncio
async def test_format_search_results(work_log_search_agent):
    mock_analyzed_results = {
        'total_count': 1,
        'results': [
            {
                'log_id': '123',
                'work_date': datetime(2025, 7, 24),
                'category': '収穫',
                'original_message': 'トマトハウスでトマトを収穫しました。',
                'extracted_data': {'field_name': 'トマトハウス', 'work_content': 'トマトを収穫'},
                'created_at': datetime(2025, 7, 24, 10, 0)
            }
        ],
        'statistics': {},
        'patterns': [],
        'recommendations': []
    }
    formatted = work_log_search_agent._format_search_results(mock_analyzed_results, {})
    assert formatted['success'] == True
    assert formatted['total_count'] == 1
    assert "日付: 2025-07-24 圃場: トマトハウス 作業内容: トマトを収穫" in formatted['results'][0]['summary']

@pytest.mark.asyncio
async def test_search_work_logs_integration(work_log_search_agent, mock_data_access):
    mock_data_access.search_work_logs.return_value = [
        {"log_id": "log1", "work_date": datetime(2025, 7, 23), "category": "防除", "original_message": "トマトハウスで防除作業", "extracted_data": {"field_name": "トマトハウス", "work_content": "防除作業"}, "created_at": datetime(2025, 7, 23)}
    ]
    response = await work_log_search_agent.search_work_logs("トマトハウスの作業記録", "user123")
    assert response['success'] == True
    assert "1件の作業記録が見つかりました。" in response['message']
    assert "日付: 2025-07-23 圃場: トマトハウス 作業内容: 防除作業" in response['results'][0]['summary']
