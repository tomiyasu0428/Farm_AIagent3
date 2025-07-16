"""
農業AIエージェントの単体テスト
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agri_ai.core.agent import AgriAIAgent


class TestAgriAIAgent:
    """AgriAIAgentのテストクラス"""
    
    @pytest.fixture
    async def agent(self):
        """テスト用エージェントの作成"""
        agent = AgriAIAgent()
        
        # MongoDBクライアントのモック
        with patch('src.agri_ai.core.agent.mongodb_client') as mock_client:
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            
            # LLMのモック
            with patch('src.agri_ai.core.agent.ChatOpenAI') as mock_llm:
                mock_llm.return_value = MagicMock()
                
                # エージェントエグゼキュータのモック
                with patch('src.agri_ai.core.agent.AgentExecutor') as mock_executor:
                    mock_executor.return_value = MagicMock()
                    mock_executor.return_value.ainvoke = AsyncMock(
                        return_value={"output": "テスト応答"}
                    )
                    
                    await agent.initialize()
                    yield agent
                    await agent.shutdown()
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent):
        """エージェントの初期化テスト"""
        assert agent.llm is not None
        assert agent.agent_executor is not None
        assert len(agent.tools) > 0
    
    @pytest.mark.asyncio
    async def test_process_message(self, agent):
        """メッセージ処理テスト"""
        response = await agent.process_message("今日のタスクは？", "test_user")
        assert response == "テスト応答"
    
    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, agent):
        """エラーハンドリングテスト"""
        # エラーを発生させる
        agent.agent_executor.ainvoke = AsyncMock(side_effect=Exception("テストエラー"))
        
        response = await agent.process_message("エラーテスト", "test_user")
        assert "エラーが発生しました" in response
    
    def test_system_prompt(self, agent):
        """システムプロンプトテスト"""
        prompt = agent._get_system_prompt()
        assert "農業管理" in prompt
        assert "AIエージェント" in prompt