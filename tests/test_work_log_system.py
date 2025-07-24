"""
作業記録システムのテスト

作業記録の登録・検索機能の包括的なテストケース
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

# テスト対象のインポート
from src.agri_ai.agents.work_log_registration_agent import WorkLogRegistrationAgent
from src.agri_ai.agents.work_log_search_agent import WorkLogSearchAgent
from src.agri_ai.services.master_data_resolver import MasterDataResolver
from src.agri_ai.services.query_analyzer import QueryAnalyzer
from src.agri_ai.langchain_tools.work_log_agent_tool import WorkLogAgentTool


class TestMasterDataResolver:
    """MasterDataResolverのテスト"""
    
    @pytest.fixture
    def resolver(self):
        return MasterDataResolver()
    
    @pytest.fixture
    def mock_fields_data(self):
        return [
            {
                "_id": "field_001",
                "field_code": "F001",
                "name": "トマトハウス"
            },
            {
                "_id": "field_002", 
                "field_code": "F002",
                "name": "第1圃場"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_resolve_field_data_exact_match(self, resolver, mock_fields_data):
        """圃場データの完全一致テスト"""
        with patch.object(resolver, '_get_fields_data', return_value=mock_fields_data):
            result = await resolver.resolve_field_data("トマトハウス")
            
            assert result['field_id'] == "field_001"
            assert result['field_name'] == "トマトハウス"
            assert result['confidence'] == 1.0
            assert result['method'] == 'exact_match'
    
    @pytest.mark.asyncio
    async def test_resolve_field_data_partial_match(self, resolver, mock_fields_data):
        """圃場データの部分一致テスト"""
        with patch.object(resolver, '_get_fields_data', return_value=mock_fields_data):
            result = await resolver.resolve_field_data("トマト")
            
            assert result['field_id'] == "field_001"
            assert result['field_name'] == "トマトハウス"
            assert result['confidence'] <= 0.8
            assert result['method'] == 'partial_match'
    
    @pytest.mark.asyncio
    async def test_resolve_field_data_no_match(self, resolver, mock_fields_data):
        """圃場データの一致なしテスト"""
        with patch.object(resolver, '_get_fields_data', return_value=mock_fields_data):
            result = await resolver.resolve_field_data("存在しない圃場")
            
            assert result['field_id'] is None
            assert result['confidence'] == 0.0
            assert result['method'] == 'no_match'


class TestQueryAnalyzer:
    """QueryAnalyzerのテスト"""
    
    @pytest.fixture
    def analyzer(self):
        return QueryAnalyzer()
    
    def test_analyze_registration_intent(self, analyzer):
        """登録意図の分析テスト"""
        test_cases = [
            ("昨日トマトハウスで防除作業をしました", "register", True),
            ("第2圃場の防除が完了しました", "register", True),
            ("ダコニール1000を散布した", "register", True),
        ]
        
        for message, expected_intent, should_be_confident in test_cases:
            result = analyzer.analyze_work_log_intent(message)
            assert result['intent'] == expected_intent
            if should_be_confident:
                assert result['confidence'] > 0.6
    
    def test_analyze_search_intent(self, analyzer):
        """検索意図の分析テスト"""
        test_cases = [
            ("先月の防除記録を教えて", "search", True),
            ("トマトハウスの作業履歴を確認したい", "search", True),
            ("ダコニール1000の使用頻度は？", "search", True),
        ]
        
        for message, expected_intent, should_be_confident in test_cases:
            result = analyzer.analyze_work_log_intent(message)
            assert result['intent'] == expected_intent
            if should_be_confident:
                assert result['confidence'] > 0.6
    
    def test_analyze_tense(self, analyzer):
        """時制分析テスト"""
        test_cases = [
            ("昨日作業しました", "past"),
            ("今日の作業は？", "present"),
            ("明日防除予定です", "future"),
            ("先月の記録を教えて？", "question"),
        ]
        
        for message, expected_tense in test_cases:
            result = analyzer.analyze_work_log_intent(message)
            tense_info = result['tense']
            assert tense_info['dominant'] in [expected_tense, 'neutral']


class TestWorkLogRegistrationAgent:
    """WorkLogRegistrationAgentのテスト"""
    
    @pytest.fixture
    def agent(self):
        return WorkLogRegistrationAgent()
    
    @pytest.fixture
    def mock_master_resolver(self):
        resolver = Mock()
        resolver.resolve_field_data = AsyncMock(return_value={
            'field_id': 'FIELD-A01',
            'field_name': 'トマトハウス',
            'confidence': 0.9,
            'method': 'exact_match'
        })
        resolver.resolve_crop_data = AsyncMock(return_value={
            'crop_id': 'CROP-001',
            'crop_name': 'トマト',
            'confidence': 0.9,
            'method': 'exact_match'
        })
        resolver.resolve_material_data = AsyncMock(return_value={
            'material_id': 'MAT-D001',
            'material_name': 'ダコニール1000',
            'confidence': 0.9,
            'method': 'exact_match'
        })
        return resolver
    
    @pytest.mark.asyncio
    async def test_extract_work_info(self, agent):
        """作業情報抽出テスト"""
        message = "昨日トマトハウスでダコニール1000を散布しました"
        
        extracted = await agent._extract_work_info(message)
        
        assert extracted['relative_date'] == '昨日'
        assert 'トマト' in extracted['raw_field_name']
        assert len(extracted['work_type_keywords']) > 0
        assert '防除' in extracted['work_type_keywords']
    
    @pytest.mark.asyncio
    async def test_parse_work_date(self, agent):
        """作業日解釈テスト"""
        test_cases = [
            ("昨日", 1),  # 1日前
            ("一昨日", 2),  # 2日前
            ("今日", 0),  # 今日
        ]
        
        for relative_date, days_ago in test_cases:
            extracted_info = {'relative_date': relative_date}
            result = agent._parse_work_date("", extracted_info)
            
            expected_date = datetime.now().date() - timedelta(days=days_ago)
            assert result == expected_date
    
    @pytest.mark.asyncio
    async def test_classify_work_type(self, agent):
        """作業分類テスト"""
        test_cases = [
            ({'work_type_keywords': ['防除']}, {}, '防除'),
            ({'work_type_keywords': ['施肥']}, {}, '施肥'),
            ({'work_type_keywords': []}, {'material_data': [{'material_name': '殺菌剤ABC'}]}, '防除'),
        ]
        
        for extracted_info, resolved_data, expected in test_cases:
            result = agent._classify_work_type(extracted_info, resolved_data)
            assert result == expected


class TestWorkLogSearchAgent:
    """WorkLogSearchAgentのテスト"""
    
    @pytest.fixture
    def agent(self):
        return WorkLogSearchAgent()
    
    @pytest.mark.asyncio
    async def test_parse_search_query(self, agent):
        """検索クエリ解析テスト"""
        test_cases = [
            ("先月の防除記録", "先月", "防除"),
            ("トマトハウスの作業履歴", None, None),
            ("過去30日の施肥作業", "過去", "施肥"),
        ]
        
        for query, expected_date, expected_work in test_cases:
            params = await agent._parse_search_query(query)
            
            if expected_date:
                assert 'date_range' in params
            if expected_work:
                assert expected_work in params.get('work_categories', [])
    
    @pytest.mark.asyncio
    async def test_analyze_results_empty(self, agent):
        """空の検索結果分析テスト"""
        analyzed = await agent._analyze_results([], {})
        
        assert analyzed['total_count'] == 0
        assert analyzed['results'] == []
        assert analyzed['statistics'] == {}
    
    @pytest.mark.asyncio
    async def test_analyze_results_with_data(self, agent):
        """データ有りの検索結果分析テスト"""
        mock_results = [
            {
                'log_id': 'LOG-001',
                'category': '防除',
                'work_date': datetime.now(),
                'extracted_data': {
                    'field_name': 'トマトハウス',
                    'material_names': ['ダコニール1000']
                }
            },
            {
                'log_id': 'LOG-002',
                'category': '施肥',
                'work_date': datetime.now(),
                'extracted_data': {
                    'field_name': 'トマトハウス',
                    'material_names': ['化成肥料']
                }
            }
        ]
        
        analyzed = await agent._analyze_results(mock_results, {})
        
        assert analyzed['total_count'] == 2
        assert analyzed['statistics']['work_categories']['防除'] == 1
        assert analyzed['statistics']['work_categories']['施肥'] == 1
        assert analyzed['statistics']['fields']['トマトハウス'] == 2
        assert analyzed['statistics']['materials']['ダコニール1000'] == 1


class TestWorkLogAgentTool:
    """WorkLogAgentToolの統合テスト"""
    
    @pytest.fixture
    def tool(self):
        return WorkLogAgentTool()
    
    @pytest.fixture
    def mock_registration_agent(self):
        agent = Mock()
        agent.register_work_log = AsyncMock(return_value={
            'success': True,
            'log_id': 'LOG-TEST-001',
            'confidence': 0.85,
            'message': '作業記録を登録しました'
        })
        return agent
    
    @pytest.fixture
    def mock_search_agent(self):
        agent = Mock()
        agent.search_work_logs = AsyncMock(return_value={
            'success': True,
            'total_count': 2,
            'results': [
                {'log_id': 'LOG-001', 'category': '防除'},
                {'log_id': 'LOG-002', 'category': '施肥'}
            ],
            'message': '2件の作業記録が見つかりました'
        })
        return agent
    
    @pytest.fixture
    def mock_query_analyzer(self):
        analyzer = Mock()
        analyzer.analyze_work_log_intent = Mock()
        return analyzer
    
    @pytest.mark.asyncio
    async def test_registration_flow(self, tool, mock_registration_agent, mock_query_analyzer):
        """登録フローテスト"""
        # 登録意図の分析結果をモック
        mock_query_analyzer.analyze_work_log_intent.return_value = {
            'intent': 'register',
            'confidence': 0.8,
            'reasoning': '過去形の作業報告'
        }
        
        with patch.object(tool, '_get_registration_agent', return_value=mock_registration_agent), \
             patch.object(tool, '_get_query_analyzer', return_value=mock_query_analyzer):
            
            result = await tool._arun("昨日防除作業を完了しました", "user-001")
            
            assert result['success'] is True
            assert result['log_id'] == 'LOG-TEST-001'
            assert 'intent_analysis' in result
            mock_registration_agent.register_work_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_flow(self, tool, mock_search_agent, mock_query_analyzer):
        """検索フローテスト"""
        # 検索意図の分析結果をモック
        mock_query_analyzer.analyze_work_log_intent.return_value = {
            'intent': 'search',
            'confidence': 0.8,
            'reasoning': '疑問形の記録確認'
        }
        
        with patch.object(tool, '_get_search_agent', return_value=mock_search_agent), \
             patch.object(tool, '_get_query_analyzer', return_value=mock_query_analyzer):
            
            result = await tool._arun("先月の防除記録を教えて", "user-001")
            
            assert result['success'] is True
            assert result['total_count'] == 2
            assert 'intent_analysis' in result
            mock_search_agent.search_work_logs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unknown_intent(self, tool, mock_query_analyzer):
        """不明な意図のテスト"""
        # 不明な意図の分析結果をモック
        mock_query_analyzer.analyze_work_log_intent.return_value = {
            'intent': 'unknown',
            'confidence': 0.3,
            'reasoning': '明確なキーワードが見つからない'
        }
        
        with patch.object(tool, '_get_query_analyzer', return_value=mock_query_analyzer):
            
            result = await tool._arun("何かよくわからないメッセージ", "user-001")
            
            assert result['success'] is False
            assert '意図を明確に判定できませんでした' in result['message']
            assert 'intent_analysis' in result


class TestWorkLogSystemIntegration:
    """作業記録システムの統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_registration_flow(self):
        """完全な登録フローテスト"""
        # 実際のコンポーネントを使用した統合テスト
        agent = WorkLogRegistrationAgent()
        
        # MongoDB接続をモック
        with patch('src.agri_ai.database.mongodb_client.create_mongodb_client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client.return_value = mock_client_instance
            
            # コレクションのモック
            mock_collection = AsyncMock()
            mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
            mock_client_instance.get_collection.return_value = mock_collection
            
            # マスターデータリゾルバーのモック
            with patch.object(agent, 'master_resolver') as mock_resolver:
                mock_resolver.resolve_field_data = AsyncMock(return_value={
                    'field_id': 'FIELD-001',
                    'field_name': 'テスト圃場',
                    'confidence': 0.9
                })
                mock_resolver.resolve_crop_data = AsyncMock(return_value={
                    'crop_id': None,
                    'crop_name': '',
                    'confidence': 0.0
                })
                mock_resolver.resolve_material_data = AsyncMock(return_value={
                    'material_id': None,
                    'material_name': '',
                    'confidence': 0.0
                })
                
                result = await agent.register_work_log(
                    "昨日テスト圃場で作業しました", "test-user"
                )
                
                assert result['success'] is True
                assert 'log_id' in result
                assert result['confidence'] >= 0.0
    
    def test_query_examples(self):
        """クエリ例のテスト"""
        analyzer = QueryAnalyzer()
        examples = analyzer.get_intent_examples()
        
        # 登録例の検証
        for example in examples['register']:
            result = analyzer.analyze_work_log_intent(example)
            assert result['intent'] == 'register'
            assert result['confidence'] > 0.5
        
        # 検索例の検証
        for example in examples['search']:
            result = analyzer.analyze_work_log_intent(example)
            assert result['intent'] == 'search'
            assert result['confidence'] > 0.5


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステスト"""
    
    @pytest.mark.asyncio
    async def test_master_data_resolver_performance(self):
        """MasterDataResolverのパフォーマンステスト"""
        resolver = MasterDataResolver()
        
        # 大量データのモック
        large_dataset = [
            {"_id": f"field_{i:03d}", "name": f"圃場{i}", "field_code": f"F{i:03d}"}
            for i in range(1000)
        ]
        
        with patch.object(resolver, '_get_fields_data', return_value=large_dataset):
            start_time = datetime.now()
            
            # 複数の検索を実行
            tasks = [
                resolver.resolve_field_data(f"圃場{i}")
                for i in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 10件の検索が1秒以内に完了することを確認
            assert duration < 1.0
            assert all(result['field_id'] is not None for result in results)
    
    def test_query_analyzer_performance(self):
        """QueryAnalyzerのパフォーマンステスト"""
        analyzer = QueryAnalyzer()
        
        test_queries = [
            "昨日トマトハウスで防除作業をしました",
            "先月の防除記録を教えて",
            "第2圃場のナスにダコニール1000を散布した",
            "トマトハウスの作業履歴を確認したい"
        ] * 25  # 100クエリ
        
        start_time = datetime.now()
        
        results = [
            analyzer.analyze_work_log_intent(query)
            for query in test_queries
        ]
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # 100クエリの分析が1秒以内に完了することを確認
        assert duration < 1.0
        assert all(result['intent'] in ['register', 'search', 'unknown'] for result in results)


if __name__ == "__main__":
    # テスト実行例
    pytest.main([__file__, "-v", "--tb=short"])