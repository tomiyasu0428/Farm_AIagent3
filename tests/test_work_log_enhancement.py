"""
作業記録高度化機能のテスト

v2.0で実装された高精度情報抽出、マスターデータ検証、確認フロー機能のテスト
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# テスト対象のインポート
from src.agri_ai.agents.models.work_log_extraction import ExtractedWorkInfo, WorkLogValidationResult
from src.agri_ai.services.work_log_extractor import WorkLogExtractor
from src.agri_ai.services.work_log_validator import WorkLogValidator
from src.agri_ai.services.work_log_confirmation import WorkLogConfirmationService
from src.agri_ai.agents.work_log_registration_agent import WorkLogRegistrationAgent


class TestExtractedWorkInfo:
    """ExtractedWorkInfoモデルのテスト"""
    
    def test_extracted_work_info_creation(self):
        """ExtractedWorkInfoの基本的な作成テスト"""
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="トマトハウス",
            crop_name="トマト",
            work_category="防除",
            materials=["ダコニール1000"],
            quantity=500.0,
            unit="L",
            confidence_score=0.85
        )
        
        assert extracted_info.work_date == "昨日"
        assert extracted_info.field_name == "トマトハウス"
        assert extracted_info.work_category == "防除"
        assert extracted_info.materials == ["ダコニール1000"]
        assert extracted_info.quantity == 500.0
        assert extracted_info.confidence_score == 0.85
    
    def test_extracted_work_info_optional_fields(self):
        """オプションフィールドのテスト"""
        extracted_info = ExtractedWorkInfo()
        
        assert extracted_info.work_date is None
        assert extracted_info.field_name is None
        assert extracted_info.materials == []
        assert extracted_info.confidence_score is None


class TestWorkLogExtractor:
    """WorkLogExtractorのテスト"""
    
    @pytest.fixture
    def extractor(self):
        """モックを使用したWorkLogExtractorのフィクスチャ"""
        # LLMをモック化
        with patch('src.agri_ai.services.work_log_extractor.ChatGoogleGenerativeAI'):
            return WorkLogExtractor()
    
    def test_confidence_score_calculation(self, extractor):
        """信頼度スコア計算のテスト"""
        # 高スコアケース
        extracted_data = {
            "work_date": "昨日",
            "field_name": "トマトハウス",
            "work_category": "防除",
            "crop_name": "トマト",
            "materials": ["ダコニール1000"],
            "quantity": 500,
            "unit": "L"
        }
        
        score = extractor._calculate_confidence_score(extracted_data)
        assert score >= 0.8  # 多くの情報が含まれているため高スコア
        
        # 低スコアケース
        minimal_data = {
            "work_date": "昨日"
        }
        
        score = extractor._calculate_confidence_score(minimal_data)
        assert score <= 0.3  # 情報が少ないため低スコア
    
    @pytest.mark.asyncio
    async def test_fallback_extraction(self, extractor):
        """フォールバック抽出のテスト"""
        message = "昨日トマトハウスで防除作業をしました"
        
        result = await extractor._fallback_extraction(message)
        
        assert isinstance(result, ExtractedWorkInfo)
        assert result.work_date == "昨日"
        assert result.work_category == "防除"
        assert result.confidence_score == 0.3  # フォールバックのため低信頼度


class TestWorkLogValidator:
    """WorkLogValidatorのテスト"""
    
    @pytest.fixture
    def validator(self):
        """モックを使用したWorkLogValidatorのフィクスチャ"""
        mock_db_connection = Mock()
        mock_master_resolver = Mock()
        
        validator = WorkLogValidator(mock_db_connection)
        validator.master_resolver = mock_master_resolver
        
        return validator
    
    @pytest.mark.asyncio
    async def test_validate_work_log_success(self, validator):
        """成功時の検証テスト"""
        # モックの設定
        validator.master_resolver.resolve_field_data = AsyncMock(return_value={
            "field_id": "FIELD-001",
            "field_name": "トマトハウス",
            "confidence": 0.9,
            "method": "exact_match"
        })
        
        validator.master_resolver.resolve_crop_data = AsyncMock(return_value={
            "crop_id": "CROP-001", 
            "crop_name": "トマト",
            "confidence": 0.9,
            "method": "exact_match"
        })
        
        validator.master_resolver.resolve_material_data = AsyncMock(return_value={
            "material_id": "MAT-001",
            "material_name": "ダコニール1000", 
            "confidence": 0.9,
            "method": "exact_match"
        })
        
        # テスト対象の実行
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="トマトハウス",
            crop_name="トマト", 
            work_category="防除",
            materials=["ダコニール1000"]
        )
        
        result = await validator.validate_work_log(extracted_info)
        
        assert isinstance(result, WorkLogValidationResult)
        assert result.is_valid == True
        assert result.field_validation["is_valid"] == True
        assert result.crop_validation["is_valid"] == True
        assert len(result.material_validation) == 1
        assert result.material_validation[0]["is_valid"] == True


class TestWorkLogConfirmationService:
    """WorkLogConfirmationServiceのテスト"""
    
    @pytest.fixture
    def confirmation_service(self):
        return WorkLogConfirmationService()
    
    def test_generate_final_confirmation(self, confirmation_service):
        """最終確認メッセージ生成のテスト"""
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="トマトハウス", 
            work_category="防除",
            confidence_score=0.9
        )
        
        validation_result = WorkLogValidationResult(
            is_valid=True,
            field_validation={
                "matched_field": {
                    "field_id": "FIELD-001",
                    "field_name": "トマトハウス"
                }
            },
            crop_validation={},
            material_validation=[],
            missing_info=[],
            suggestions=[]
        )
        
        confirmation_data = confirmation_service.generate_confirmation_message(
            extracted_info, validation_result
        )
        
        assert "以下の内容で作業記録を登録しますか？" in confirmation_data.confirmation_message
        assert "作業日: 昨日" in confirmation_data.confirmation_message
        assert "圃場: トマトハウス" in confirmation_data.confirmation_message
        assert len(confirmation_data.options) >= 2  # 登録する、修正するなど
    
    def test_generate_ambiguity_resolution(self, confirmation_service):
        """曖昧性解決メッセージ生成のテスト"""
        extracted_info = ExtractedWorkInfo(
            work_date="昨日",
            field_name="不明な圃場"
        )
        
        validation_result = WorkLogValidationResult(
            is_valid=False,
            field_validation={
                "is_valid": False,
                "input_field": "不明な圃場",
                "candidates": [
                    {"field_id": "F1", "name": "第1圃場"},
                    {"field_id": "F2", "name": "第2圃場"}
                ]
            },
            crop_validation={},
            material_validation=[],
            missing_info=["作業分類"],
            suggestions=["どのような作業でしょうか？"]
        )
        
        confirmation_data = confirmation_service.generate_confirmation_message(
            extracted_info, validation_result
        )
        
        assert "いくつか確認したいことがあります" in confirmation_data.confirmation_message
        assert "第1圃場" in confirmation_data.confirmation_message
        assert "第2圃場" in confirmation_data.confirmation_message


class TestWorkLogRegistrationAgentV2:
    """WorkLogRegistrationAgent v2.0のテスト"""
    
    @pytest.fixture
    def registration_agent(self):
        """モックを使用したWorkLogRegistrationAgentのフィクスチャ"""
        mock_db_connection = Mock()
        agent = WorkLogRegistrationAgent(mock_db_connection)
        return agent
    
    def test_parse_enhanced_work_date(self, registration_agent):
        """高度化された作業日解釈のテスト"""
        # 相対日付のテスト
        today = datetime.now()
        
        result = registration_agent._parse_enhanced_work_date("昨日")
        expected = today - registration_agent.__class__._parse_enhanced_work_date.__defaults__[0]  # timedelta(days=1)
        # 日付部分のみを比較（時刻は無視）
        assert result.date() == (today - registration_agent.__class__.__dict__['_parse_enhanced_work_date'].__annotations__['work_date_str'])
        
        result = registration_agent._parse_enhanced_work_date("今日")
        assert result.date() == today.date()
        
        # 具体的な日付のテスト
        result = registration_agent._parse_enhanced_work_date("2025-07-25")
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 25
        
        # 不正な日付のテスト（デフォルト = 今日）
        result = registration_agent._parse_enhanced_work_date("無効な日付")
        assert result.date() == today.date()


class TestIntegration:
    """統合テスト"""
    
    @pytest.mark.asyncio
    async def test_enhanced_registration_flow_integration(self):
        """高度化された登録フローの統合テスト"""
        # このテストは実際のデータベース接続が必要なため、
        # CI/CD環境では別途設定が必要
        
        # モックを使用した基本的な統合テスト
        with patch('src.agri_ai.services.work_log_extractor.WorkLogExtractor') as mock_extractor_class, \
             patch('src.agri_ai.services.work_log_validator.WorkLogValidator') as mock_validator_class, \
             patch('src.agri_ai.dependencies.database.DatabaseConnection') as mock_db_connection:
            
            # モックの設定
            mock_extractor = AsyncMock()
            mock_extractor.extract_work_information.return_value = ExtractedWorkInfo(
                work_date="昨日",
                field_name="トマトハウス",
                work_category="防除",
                confidence_score=0.9
            )
            mock_extractor_class.return_value = mock_extractor
            
            mock_validator = AsyncMock()
            mock_validator.validate_work_log.return_value = WorkLogValidationResult(
                is_valid=True,
                field_validation={},
                crop_validation={},
                material_validation=[],
                missing_info=[],
                suggestions=[]
            )
            mock_validator_class.return_value = mock_validator
            
            # テスト対象の実行
            agent = WorkLogRegistrationAgent()
            
            # モックでデータベース保存をスキップ
            with patch.object(agent, '_save_enhanced_work_log', return_value={
                'log_id': 'TEST-LOG-001',
                'extracted_data': {'field_name': 'トマトハウス'}
            }):
                result = await agent.register_work_log(
                    "昨日トマトハウスで防除作業をしました", 
                    "test_user"
                )
            
            # 結果の検証
            assert result['success'] == True
            assert result['registration_type'] == 'auto'  # 高信頼度のため自動登録
            assert 'log_id' in result


if __name__ == "__main__":
    # テスト実行例
    pytest.main([__file__, "-v", "--tb=short"])