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
        """非同期的にツールを実行する（v2.0対応）"""
        logger.info(f"Executing WorkLogRegistrationAgentTool v2.0 for user {user_id}")
        try:
            # 専門エージェントに処理を委譲
            agent = self._get_agent()
            result = await agent.register_work_log(message=message, user_id=user_id)

            if isinstance(result, dict):
                if result.get("success"):
                    # v2.0: 確認フローの対応
                    if result.get("requires_confirmation"):
                        return self._format_confirmation_response(result)
                    else:
                        return self._format_success_response(result)
                else:
                    return self._format_error_response(result)
            else:
                return str(result)

        except Exception as e:
            logger.error(f"Error in WorkLogRegistrationAgentTool: {e}")
            return f"作業記録登録ツールでエラーが発生しました: {e}"
    
    def _format_success_response(self, result: dict) -> str:
        """成功レスポンスの整形"""
        message_parts = []
        
        # 基本メッセージ
        message_parts.append(result.get("message", "作業記録を正常に登録しました。"))
        
        # 信頼度スコア表示
        if result.get("confidence_score"):
            confidence_percent = int(result["confidence_score"] * 100)
            message_parts.append(f"📊 抽出精度: {confidence_percent}%")
        
        # 登録タイプ
        registration_type = result.get("registration_type", "")
        if registration_type == "auto":
            message_parts.append("✨ 高精度抽出により自動登録されました")
        elif registration_type == "confirmed":
            message_parts.append("✅ 確認済みで登録されました")
        
        # 抽出データの要約
        if result.get("extracted_data"):
            extracted = result["extracted_data"]
            summary_parts = []
            
            if extracted.get("field_name"):
                summary_parts.append(f"🏠 {extracted['field_name']}")
            if extracted.get("crop_name"):
                summary_parts.append(f"🌱 {extracted['crop_name']}")
            if extracted.get("material_names"):
                materials = ", ".join(extracted["material_names"][:2])  # 最初の2つまで
                if len(extracted["material_names"]) > 2:
                    materials += f" 他{len(extracted['material_names'])-2}件"
                summary_parts.append(f"🧪 {materials}")
            
            if summary_parts:
                message_parts.append("📝 " + " | ".join(summary_parts))
        
        return "\n".join(message_parts)
    
    def _format_confirmation_response(self, result: dict) -> str:
        """確認フロー用レスポンスの整形"""
        confirmation_data = result.get("confirmation_data", {})
        
        message_parts = []
        message_parts.append("🤔 いくつか確認したい点があります")
        
        # 信頼度が低い場合の説明
        if result.get("confidence_score", 1.0) < 0.8:
            confidence_percent = int(result.get("confidence_score", 0) * 100)
            message_parts.append(f"📊 抽出精度: {confidence_percent}% (要確認)")
        
        # 確認メッセージ
        if confirmation_data.get("message"):
            message_parts.append("")
            message_parts.append(confirmation_data["message"])
        
        # オプションの簡易表示（LINE環境での制限を考慮）
        options = confirmation_data.get("options", [])
        if options:
            message_parts.append("")
            message_parts.append("⚡ 対応可能な操作:")
            for i, option in enumerate(options[:3], 1):  # 最初の3つまで
                label = option.get("label", f"選択肢{i}")
                message_parts.append(f"{i}. {label}")
        
        message_parts.append("")
        message_parts.append("💡 詳細な情報を教えていただくか、そのまま登録することも可能です。")
        
        return "\n".join(message_parts)
    
    def _format_error_response(self, result: dict) -> str:
        """エラーレスポンスの整形"""
        error_message = result.get("message", "作業記録の登録に失敗しました。")
        
        message_parts = [f"❌ {error_message}"]
        
        # 詳細エラー情報があれば追加
        if result.get("error"):
            message_parts.append(f"詳細: {result['error']}")
        
        message_parts.append("")
        message_parts.append("🔄 より詳細な情報を含めて再度お試しください。")
        message_parts.append("例: 「昨日、トマトハウスでダコニール1000を500L散布しました」")
        
        return "\n".join(message_parts)
