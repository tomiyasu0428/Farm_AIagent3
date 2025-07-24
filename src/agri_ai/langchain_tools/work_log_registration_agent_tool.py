# src/agri_ai/langchain_tools/work_log_registration_agent_tool.py

"""
WorkLogRegistrationAgentを呼び出すためのカスタムツール
"""

import logging
from typing import Any, Dict, Type
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from ..agents.work_log_registration_agent import WorkLogRegistrationAgent

logger = logging.getLogger(__name__)

class WorkLogRegistrationToolInput(BaseModel):
    """WorkLogRegistrationAgentToolの入力スキーマ"""
    message: str = Field(description="作業記録に関するユーザーからの元の報告メッセージ")
    user_id: str = Field(description="作業を報告したユーザーのID")

class WorkLogRegistrationAgentTool(BaseTool):
    """MasterAgentがWorkLogRegistrationAgentを呼び出すためのツール"""
    name: str = "work_log_registration_agent_tool"
    description: str = """
    ユーザーからの自然言語での作業報告（「昨日トマトに薬を撒いた」など）を受け取り、
    それを構造化データとしてデータベースに記録するために使用します。
    作業の完了報告、日々の作業ログの保存などに使用してください。
    """
    args_schema: Type[BaseModel] = WorkLogRegistrationToolInput
    agent: WorkLogRegistrationAgent

    def __init__(self, agent: WorkLogRegistrationAgent):
        super().__init__()
        self.agent = agent

    def _run(self, message: str, user_id: str) -> Dict[str, Any]:
        """同期的にツールを実行する（非推奨）"""
        import asyncio
        return asyncio.run(self._arun(message=message, user_id=user_id))

    async def _arun(self, message: str, user_id: str) -> Dict[str, Any]:
        """非同期的にツールを実行する"""
        logger.info(f"Executing WorkLogRegistrationAgentTool for user {user_id}")
        try:
            # 専門エージェントに処理を委譲
            result = await self.agent.register_work_log(message=message, user_id=user_id)
            return result
        except Exception as e:
            logger.error(f"Error in WorkLogRegistrationAgentTool: {e}")
            return {"success": False, "error": str(e)}
