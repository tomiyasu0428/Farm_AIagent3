"""
リファクタリング完了後の統合テスト

v3.0アーキテクチャの各コンポーネントが正しく連携することを確認
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# テスト対象のインポート
from src.agri_ai.agents.work_log_registration_agent import WorkLogRegistrationAgent
from src.agri_ai.services.work_log_extractor import WorkLogExtractor
from src.agri_ai.services.work_log_validator_v2 import WorkLogValidator
from src.agri_ai.domain.work_info_scorer import WorkInfoScorer
from src.agri_ai.domain.master_data_matcher import MasterDataMatcher
from src.agri_ai.gateways.llm_extraction_gateway import LLMExtractionGateway
from src.agri_ai.gateways.master_data_gateway import MasterDataGateway
from src.agri_ai.strategies.strategy_factory import RegistrationStrategyFactory
from src.agri_ai.providers.service_provider import ServiceProvider
from src.agri_ai.dependencies.database import DatabaseConnection
from src.agri_ai.agents.models.work_log_extraction import ExtractedWorkInfo, WorkLogValidationResult


class TestRefactoredWorkLogSystem:
    """リファクタリング後のワークログシステム統合テスト"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """モックデータベース接続"""
        return Mock(spec=DatabaseConnection)
    
    @pytest.fixture
    def mock_llm_gateway(self):
        """モックLLMゲートウェイ"""
        gateway = Mock(spec=LLMExtractionGateway)
        gateway.call_function_calling = AsyncMock(return_value={
            'work_date': '昨日',
            'field_name': 'トマトハウス1',
            'crop_name': 'トマト',
            'work_category': '防除',
            'materials': ['ダコニール1000'],
            'quantity': 500.0,
            'unit': 'ml',
            'notes': 'うどんこ病対策'
        })
        return gateway
    
    @pytest.fixture
    def mock_master_data_gateway(self):
        """モックマスターデータゲートウェイ"""
        gateway = Mock(spec=MasterDataGateway)
        
        # サンプルマスターデータ
        gateway.get_all_fields = AsyncMock(return_value=[
            {
                'field_id': 'FIELD001',
                'field_name': 'トマトハウス1',
                'field_code': 'TH01',
                'status': 'active'
            }
        ])
        
        gateway.get_all_crops = AsyncMock(return_value=[
            {
                'crop_id': 'CROP001',
                'crop_name': 'トマト',
                'scientific_name': 'Solanum lycopersicum',
                'aliases': ['とまと', '完熟トマト'],
                'status': 'active'
            }
        ])
        
        gateway.get_all_materials = AsyncMock(return_value=[
            {
                'material_id': 'MAT001',
                'material_name': 'ダコニール1000',
                'brand_name': 'ダコニール',
                'active_ingredients': ['クロロタロニル'],
                'status': 'active'
            }
        ])
        
        return gateway
    
    @pytest.fixture
    def work_info_scorer(self):
        """ワーク情報スコアラー"""
        return WorkInfoScorer()
    
    @pytest.fixture
    def master_data_matcher(self):
        """マスターデータマッチャー"""
        return MasterDataMatcher()
    
    @pytest.fixture
    def work_log_extractor(self, mock_llm_gateway, work_info_scorer):
        """ワークログ抽出器"""
        return WorkLogExtractor(gateway=mock_llm_gateway, scorer=work_info_scorer)
    
    @pytest.fixture
    def work_log_validator(self, mock_master_data_gateway, master_data_matcher):
        """ワークログバリデーター"""
        return WorkLogValidator(gateway=mock_master_data_gateway, matcher=master_data_matcher)
    
    @pytest.fixture
    def mock_service_provider(self, work_log_extractor, work_log_validator):
        """モックサービスプロバイダー"""
        provider = Mock(spec=ServiceProvider)
        provider.get_work_log_extractor.return_value = work_log_extractor
        provider.get_work_log_validator.return_value = work_log_validator
        
        # 他のサービスもモック
        provider.get_intelligent_decision_service.return_value = Mock()
        provider.get_work_log_confirmation_service.return_value = Mock()
        
        return provider
    
    @pytest.fixture
    def work_log_agent(self, mock_service_provider, mock_db_connection):
        """ワークログ登録エージェント"""
        return WorkLogRegistrationAgent(
            service_provider=mock_service_provider,
            db_connection=mock_db_connection
        )

    @pytest.mark.asyncio
    async def test_end_to_end_work_log_registration_flow(
        self, 
        work_log_agent,
        mock_db_connection
    ):
        """エンドツーエンドの作業記録登録フロー"""
        
        # データベース保存をモック
        mock_collection = AsyncMock()
        mock_client = AsyncMock()
        mock_client.get_collection.return_value = mock_collection
        mock_db_connection.get_client = AsyncMock(return_value=mock_client)
        
        # テスト実行
        test_message = "昨日、トマトハウス1でトマトにダコニール1000を500ml散布しました。うどんこ病対策です。"
        test_user_id = "user123"
        
        result = await work_log_agent.register_work_log(test_message, test_user_id)
        
        # 結果検証
        assert result['success'] is True
        assert 'log_id' in result
        assert result['confidence_score'] > 0.5  # 高信頼度
        assert result['registration_type'] in ['auto', 'confirmation_required']
    
    @pytest.mark.asyncio
    async def test_work_info_extraction_component(self, work_log_extractor):
        """作業情報抽出コンポーネントのテスト"""
        
        test_message = "昨日、トマトハウス1でトマトにダコニール1000を500ml散布しました。"
        
        extracted_info = await work_log_extractor.extract_work_information(test_message)
        
        # 抽出結果検証
        assert isinstance(extracted_info, ExtractedWorkInfo)
        assert extracted_info.work_date == '昨日'
        assert extracted_info.field_name == 'トマトハウス1'
        assert extracted_info.crop_name == 'トマト'
        assert extracted_info.work_category == '防除'
        assert 'ダコニール1000' in extracted_info.materials
        assert extracted_info.quantity == 500.0
        assert extracted_info.unit == 'ml'
        assert extracted_info.confidence_score > 0.0
    
    @pytest.mark.asyncio
    async def test_work_log_validation_component(self, work_log_validator):
        """作業記録バリデーションコンポーネントのテスト"""
        
        # テスト用抽出情報
        extracted_info = ExtractedWorkInfo(
            work_date='昨日',
            field_name='トマトハウス1',
            crop_name='トマト',
            work_category='防除',
            materials=['ダコニール1000'],
            quantity=500.0,
            unit='ml',
            notes='うどんこ病対策',
            confidence_score=0.85
        )
        
        validation_result = await work_log_validator.validate_work_log(extracted_info)
        
        # バリデーション結果検証
        assert isinstance(validation_result, WorkLogValidationResult)
        assert validation_result.is_valid is True
        assert validation_result.field_validation['matched_field'] is not None
        assert validation_result.crop_validation['matched_crop'] is not None
        assert len(validation_result.material_validation) > 0
        assert validation_result.quality_score > 0.5
    
    def test_master_data_matcher_component(self, master_data_matcher):
        """マスターデータマッチャーコンポーネントのテスト"""
        
        # サンプルマスターデータ
        master_fields = [
            {
                'field_id': 'FIELD001',
                'field_name': 'トマトハウス1',
                'field_code': 'TH01'
            }
        ]
        
        # マッチングテスト
        result = master_data_matcher.match_field_data('トマトハウス1', master_fields)
        
        # マッチング結果検証
        assert result['matched_field'] is not None
        assert result['matched_field']['confidence'] >= 0.8
        assert result['match_quality'] in ['exact', 'high']
        assert result['ambiguity_detected'] is False
    
    def test_work_info_scorer_component(self, work_info_scorer):
        """ワーク情報スコアラーコンポーネントのテスト"""
        
        # テスト用データ
        extracted_data = {
            'work_date': '昨日',
            'field_name': 'トマトハウス1',
            'crop_name': 'トマト',
            'work_category': '防除',
            'materials': ['ダコニール1000'],
            'quantity': 500.0,
            'unit': 'ml'
        }
        
        confidence_score = work_info_scorer.calculate_confidence_score(extracted_data)
        
        # スコア結果検証
        assert 0.0 <= confidence_score <= 1.0
        assert confidence_score > 0.5  # 完全なデータなので高スコア期待
        
        # スコア内訳も確認
        breakdown = work_info_scorer.get_score_breakdown(extracted_data)
        assert len(breakdown) > 0
        assert all(0.0 <= score <= 1.0 for score in breakdown.values())
    
    @pytest.mark.asyncio
    async def test_strategy_pattern_integration(self, work_log_agent, mock_db_connection):
        """戦略パターンの統合テスト"""
        
        # データベース保存をモック
        mock_collection = AsyncMock()
        mock_client = AsyncMock()
        mock_client.get_collection.return_value = mock_collection
        mock_db_connection.get_client = AsyncMock(return_value=mock_client)
        
        # 高信頼度データのテスト（自動登録戦略）
        high_confidence_message = "昨日、トマトハウス1でトマトにダコニール1000を500ml散布しました。"
        result = await work_log_agent.register_work_log(high_confidence_message, "user123")
        
        assert result['success'] is True
        assert 'strategy_used' in result or result['registration_type'] == 'auto'
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, work_log_agent):
        """エラーハンドリングの統合テスト"""
        
        # 不正なメッセージでのテスト
        invalid_message = ""
        result = await work_log_agent.register_work_log(invalid_message, "user123")
        
        # エラー処理の確認
        assert 'success' in result
        # エラーでも適切にハンドリングされることを確認
    
    @pytest.mark.asyncio
    async def test_dependency_injection_integration(self, mock_service_provider, mock_db_connection):
        """依存性注入の統合テスト"""
        
        # カスタムサービスプロバイダーでエージェント作成
        agent = WorkLogRegistrationAgent(
            service_provider=mock_service_provider,
            db_connection=mock_db_connection
        )
        
        # 依存関係の確認
        assert agent.service_provider == mock_service_provider
        assert agent.db_connection == mock_db_connection
        assert agent.strategy_factory is not None
        assert agent.strategy_context is not None
    
    def test_component_isolation(self, work_info_scorer, master_data_matcher):
        """コンポーネント分離の確認テスト"""
        
        # ドメインロジッククラスがI/Oに依存していないことを確認
        
        # WorkInfoScorerの分離確認
        assert not hasattr(work_info_scorer, 'db_connection')
        assert not hasattr(work_info_scorer, 'llm')
        
        # MasterDataMatcherの分離確認
        assert not hasattr(master_data_matcher, 'db_connection')
        assert not hasattr(master_data_matcher, 'api_client')
        
        # 純粋関数的な動作確認
        test_data = {'work_date': '今日', 'field_name': 'テスト圃場'}
        score1 = work_info_scorer.calculate_confidence_score(test_data)
        score2 = work_info_scorer.calculate_confidence_score(test_data)
        assert score1 == score2  # 同じ入力は同じ出力
    
    @pytest.mark.asyncio
    async def test_performance_expectations(self, work_log_agent, mock_db_connection):
        """パフォーマンス期待値のテスト"""
        
        import time
        
        # データベース保存をモック
        mock_collection = AsyncMock()
        mock_client = AsyncMock()
        mock_client.get_collection.return_value = mock_collection
        mock_db_connection.get_client = AsyncMock(return_value=mock_client)
        
        test_message = "昨日、トマトハウス1でトマトにダコニール1000を500ml散布しました。"
        
        start_time = time.time()
        result = await work_log_agent.register_work_log(test_message, "user123")
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # パフォーマンス確認（3秒以内の要件）
        assert execution_time < 3.0, f"実行時間が3秒を超過: {execution_time:.2f}秒"
        assert result['success'] is True


if __name__ == "__main__":
    # 単体実行用
    pytest.main([__file__, "-v"])