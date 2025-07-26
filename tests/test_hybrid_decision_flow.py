"""
ハイブリッド判断フローのテスト

固定ルールとLLM知的判断の組み合わせが適切に動作することを確認
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# テスト対象のインポート
from src.agri_ai.agents.models.work_log_extraction import ExtractedWorkInfo, WorkLogValidationResult
from src.agri_ai.services.intelligent_decision_service import IntelligentDecisionService, ContextAnalysis
from src.agri_ai.agents.work_log_registration_agent import WorkLogRegistrationAgent


class TestHybridDecisionFlow:
    """ハイブリッド判断フローのテスト"""
    
    @pytest.fixture
    def mock_registration_agent(self):
        """モックを使用したWorkLogRegistrationAgentのフィクスチャ"""
        mock_db_connection = Mock()
        agent = WorkLogRegistrationAgent(mock_db_connection)
        return agent
    
    @pytest.mark.asyncio
    async def test_high_confidence_direct_registration(self, mock_registration_agent):
        """高信頼度ケース: 直接登録"""
        
        # 高信頼度のExtractedWorkInfo
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="トマトハウス",
            crop_name="トマト",
            work_category="防除",
            materials=["ダコニール1000"],
            quantity=500.0,
            unit="L",
            confidence_score=0.92
        )
        
        # 検証成功のValidationResult
        validation_result = WorkLogValidationResult(
            is_valid=True,
            field_validation={"matched_field": {"field_id": "F1", "field_name": "トマトハウス"}},
            crop_validation={"matched_crop": {"crop_id": "C1", "crop_name": "トマト"}},
            material_validation=[{"matched_material": {"material_id": "M1", "material_name": "ダコニール1000"}}],
            missing_info=[],
            suggestions=[]
        )
        
        # _direct_registrationをモック化
        with patch.object(mock_registration_agent, '_direct_registration', 
                         return_value={'success': True, 'registration_type': 'auto'}) as mock_direct:
            
            result = await mock_registration_agent._hybrid_decision_flow(
                extracted_info, validation_result, "昨日トマトハウスでダコニール1000を500L散布", "test_user"
            )
            
            # 直接登録が呼ばれることを確認
            mock_direct.assert_called_once()
            assert result['success'] == True
            assert result['registration_type'] == 'auto'
    
    @pytest.mark.asyncio
    async def test_low_confidence_confirmation_flow(self, mock_registration_agent):
        """低信頼度ケース: 確認フロー"""
        
        # 低信頼度のExtractedWorkInfo
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="不明な場所",
            confidence_score=0.3  # 低信頼度
        )
        
        validation_result = WorkLogValidationResult(
            is_valid=False,
            field_validation={"is_valid": False},
            crop_validation={},
            material_validation=[],
            missing_info=["圃場", "作物", "作業分類"],
            suggestions=[]
        )
        
        # _confirmation_flowをモック化
        with patch.object(mock_registration_agent, '_confirmation_flow',
                         return_value={'success': True, 'requires_confirmation': True}) as mock_confirm:
            
            result = await mock_registration_agent._hybrid_decision_flow(
                extracted_info, validation_result, "昨日適当に作業した", "test_user"
            )
            
            # 確認フローが呼ばれることを確認
            mock_confirm.assert_called_once()
            assert result['requires_confirmation'] == True
    
    @pytest.mark.asyncio
    async def test_gray_zone_llm_decision(self, mock_registration_agent):
        """グレーゾーンケース: LLM判断使用"""
        
        # グレーゾーン信頼度のExtractedWorkInfo
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="ハウス",  # 曖昧
            crop_name="トマト",
            work_category="防除",
            confidence_score=0.6  # グレーゾーン
        )
        
        validation_result = WorkLogValidationResult(
            is_valid=False,
            field_validation={"is_valid": False, "candidates": [{"name": "トマトハウス"}]},
            crop_validation={"is_valid": True},
            material_validation=[],
            missing_info=["圃場詳細"],
            suggestions=[]
        )
        
        # IntelligentDecisionServiceをモック化
        mock_context_analysis = ContextAnalysis(
            should_override=True,
            recommended_action="auto_register_inferred",
            confidence=0.8,
            reasoning="文脈から「ハウス」は「トマトハウス」と推測可能",
            urgency_level="medium",
            missing_info_inference={"field_name": "トマトハウス"}
        )
        
        with patch('src.agri_ai.services.intelligent_decision_service.IntelligentDecisionService') as MockService:
            mock_service = MockService.return_value
            mock_service.should_use_intelligent_decision = AsyncMock(return_value=True)
            mock_service.get_user_recent_history = AsyncMock(return_value=[])
            mock_service.analyze_context = AsyncMock(return_value=mock_context_analysis)
            
            with patch.object(mock_registration_agent, '_direct_registration',
                             return_value={'success': True, 'registration_type': 'llm_inferred'}) as mock_direct:
                
                result = await mock_registration_agent._hybrid_decision_flow(
                    extracted_info, validation_result, "昨日ハウスでトマトに防除", "test_user"
                )
                
                # LLM判断により直接登録が実行されることを確認
                mock_service.should_use_intelligent_decision.assert_called_once()
                mock_service.analyze_context.assert_called_once()
                mock_direct.assert_called_once()
                assert result['success'] == True
    
    @pytest.mark.asyncio
    async def test_urgent_keyword_llm_activation(self, mock_registration_agent):
        """緊急キーワードでLLM判断活性化"""
        
        extracted_info = ExtractedWorkInfo(
            work_date="今日",
            field_name="トマトハウス",
            crop_name="トマト", 
            confidence_score=0.6  # 通常なら確認フロー
        )
        
        validation_result = WorkLogValidationResult(
            is_valid=True,
            field_validation={"is_valid": True},
            crop_validation={"is_valid": True},
            material_validation=[],
            missing_info=[],
            suggestions=[]
        )
        
        # 緊急性を示すメッセージ
        urgent_message = "トマトハウスのトマトが病気になっています！至急対応が必要です"
        
        mock_context_analysis = ContextAnalysis(
            should_override=True,
            recommended_action="auto_register_urgent",
            confidence=0.9,
            reasoning="緊急性が高く即座に登録すべき",
            urgency_level="critical"
        )
        
        with patch('src.agri_ai.services.intelligent_decision_service.IntelligentDecisionService') as MockService:
            mock_service = MockService.return_value
            mock_service.should_use_intelligent_decision = AsyncMock(return_value=True)
            mock_service.get_user_recent_history = AsyncMock(return_value=[])
            mock_service.analyze_context = AsyncMock(return_value=mock_context_analysis)
            
            with patch.object(mock_registration_agent, '_direct_registration',
                             return_value={'success': True, 'registration_type': 'urgent'}) as mock_direct:
                
                result = await mock_registration_agent._hybrid_decision_flow(
                    extracted_info, validation_result, urgent_message, "test_user"
                )
                
                # 緊急ケースとして直接登録されることを確認
                mock_service.should_use_intelligent_decision.assert_called_once()
                mock_direct.assert_called_once()
                assert result['registration_type'] == 'urgent'


class TestIntelligentDecisionService:
    """IntelligentDecisionServiceの単体テスト"""
    
    @pytest.fixture
    def decision_service(self):
        return IntelligentDecisionService()
    
    @pytest.mark.asyncio
    async def test_should_use_intelligent_decision_gray_zone(self, decision_service):
        """グレーゾーン信頼度でLLM判断が必要と判定"""
        
        extracted_info = ExtractedWorkInfo(confidence_score=0.6)  # グレーゾーン
        validation_result = WorkLogValidationResult(
            is_valid=True, field_validation={}, crop_validation={}, 
            material_validation=[], missing_info=[], suggestions=[]
        )
        
        result = await decision_service.should_use_intelligent_decision(
            "普通のメッセージ", extracted_info, validation_result
        )
        
        assert result == True
    
    @pytest.mark.asyncio 
    async def test_should_use_intelligent_decision_urgent_keywords(self, decision_service):
        """緊急キーワードでLLM判断が必要と判定"""
        
        extracted_info = ExtractedWorkInfo(confidence_score=0.9)  # 高信頼度でも
        validation_result = WorkLogValidationResult(
            is_valid=True, field_validation={}, crop_validation={},
            material_validation=[], missing_info=[], suggestions=[]
        )
        
        # 緊急キーワード含むメッセージ
        urgent_message = "トマトが病気で枯れそうです"
        
        result = await decision_service.should_use_intelligent_decision(
            urgent_message, extracted_info, validation_result
        )
        
        assert result == True
    
    @pytest.mark.asyncio
    async def test_should_not_use_intelligent_decision_high_confidence(self, decision_service):
        """高信頼度ではLLM判断不要と判定"""
        
        extracted_info = ExtractedWorkInfo(confidence_score=0.9)
        validation_result = WorkLogValidationResult(
            is_valid=True, field_validation={}, crop_validation={},
            material_validation=[], missing_info=[], suggestions=[]
        )
        
        result = await decision_service.should_use_intelligent_decision(
            "普通のメッセージ", extracted_info, validation_result
        )
        
        assert result == False


if __name__ == "__main__":
    # テスト実行例
    pytest.main([__file__, "-v", "--tb=short"])