# src/agri_ai/langchain_tools/work_log_registration_agent_tool.py

"""
WorkLogRegistrationAgentを呼び出すためのカスタムツール
"""

import logging
from typing import Type, Any
from pydantic import BaseModel, Field
from .base_tool import AgriAIBaseTool

logger = logging.getLogger(__name__)


class WorkLogRegistrationToolInput(BaseModel):
    """WorkLogRegistrationAgentToolの入力スキーマ"""

    message: str = Field(description="作業記録に関するユーザーからの元の報告メッセージ")
    user_id: str = Field(description="作業を報告したユーザーのID")


# Private attribute for holding agent instance


class WorkLogRegistrationAgentTool(AgriAIBaseTool):
    """MasterAgentがWorkLogRegistrationAgentを呼び出すためのツール"""

    name: str = "work_log_registration_agent_tool"
    description: str = """
    ユーザーからの自然言語での作業報告（「昨日トマトに薬を撒いた」など）を受け取り、
    それを構造化データとしてデータベースに記録するために使用します。
    作業の完了報告、日々の作業ログの保存などに使用してください。
    """
    args_schema: Type[BaseModel] = WorkLogRegistrationToolInput
    # Private attribute to hold agent instance (not treated as a pydantic field)
    _work_log_registration_agent: Any = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_agent(self):
        """遅延インポートでWorkLogRegistrationAgentを取得"""
        if self._work_log_registration_agent is None:
            from ..agents.work_log_registration_agent import WorkLogRegistrationAgent

            self._work_log_registration_agent = WorkLogRegistrationAgent()
        return self._work_log_registration_agent

    async def _arun(self, query: str = "", **kwargs) -> str:
        """非同期実行（AgriAIBaseToolと互換性を保つ）"""
        # kwargs から message と user_id を取得
        message = kwargs.get('message', query)
        user_id = kwargs.get('user_id', 'unknown_user')
        
        return await self._execute_work_log_registration(message=message, user_id=user_id)
    
    async def _execute_work_log_registration(self, message: str, user_id: str) -> str:
        """非同期的にツールを実行する"""
        logger.info(f"Executing WorkLogRegistrationAgentTool for user {user_id}")
        try:
            # 専門エージェントに処理を委譲
            agent = self._get_agent()
            result = await agent.register_work_log(message=message, user_id=user_id)

            if isinstance(result, dict):
                if result.get("success"):
                    return result.get("message", "作業記録を正常に登録しました。")
                else:
                    return result.get("error", "作業記録の登録に失敗しました。")
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Error in WorkLogRegistrationAgentTool: {e}")
            return f"作業記録登録ツールでエラーが発生しました: {e}"
