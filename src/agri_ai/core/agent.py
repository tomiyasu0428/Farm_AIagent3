"""
LangChainエージェントのコア実装
"""

import os

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

from .config import settings
from ..langchain_tools.task_lookup_tool import TaskLookupTool
from ..langchain_tools.task_update_tool import TaskUpdateTool
from ..langchain_tools.field_info_tool import FieldInfoTool
from ..langchain_tools.crop_material_tool import CropMaterialTool
from ..langchain_tools.work_suggestion_tool import WorkSuggestionTool
from ..database.mongodb_client import mongodb_client

logger = logging.getLogger(__name__)


class AgriAIAgent:
    """農業AI エージェント"""

    def __init__(self):
        self.llm = None
        self.agent_executor = None
        self.tools = []

    def initialize(self):
        """エージェントの初期化"""
        # LangSmith トレーシングの設定
        if settings.langsmith.tracing_enabled:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = settings.langsmith.api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.langsmith.project_name
            os.environ["LANGCHAIN_ENDPOINT"] = settings.langsmith.endpoint
            logger.info(
                f"LangSmith トレーシングが有効になりました。プロジェクト: {settings.langsmith.project_name}"
            )

        # データベース接続
        # MongoDB接続（非同期メソッドを同期関数内で実行）
        import asyncio

        if not mongodb_client.is_connected:
            try:
                asyncio.run(mongodb_client.connect())
            except RuntimeError:
                # 既にイベントループが存在する場合は新しいタスクとして実行
                loop = asyncio.get_event_loop()
                loop.run_until_complete(mongodb_client.connect())

        # ツールの初期化
        self._initialize_tools()

        # LLMの初期化
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.1, google_api_key=settings.google_api_key
        )

        # エージェントの作成
        self._initialize_agent()
        logger.info("農業AIエージェントの初期化が完了しました")

    def _initialize_tools(self):
        """ツールの初期化"""
        self.tools = [
            TaskLookupTool(),
            TaskUpdateTool(),
            FieldInfoTool(),
            CropMaterialTool(),
            WorkSuggestionTool(),
            # 他のツールも順次追加
        ]

    def _initialize_agent(self):
        """エージェントの作成とエグゼキュータの初期化"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self._get_system_prompt()),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_openai_tools_agent(self.llm, self.tools, prompt)

        self.agent_executor = AgentExecutor(
            agent=agent, tools=self.tools, verbose=True, handle_parsing_errors=True, max_iterations=5
        )

    def _get_system_prompt(self) -> str:
        """システムプロンプトの取得"""
        return """
あなたは農業管理を支援するAIエージェントです。
農業従事者からのLINEでの問い合わせに対して、適切な農業作業の指示や情報を提供します。

利用可能なツール：
1. task_lookup: 今日のタスクや作業予定を検索
2. task_update: 作業の完了報告や延期処理
3. field_info: 圃場の詳細情報や作付け状況を取得
4. crop_material: 作物と資材の対応関係、希釈倍率を検索
5. work_suggestion: 作業提案、農薬ローテーション、天候を考慮した作業計画

主な責務：
1. 作業タスクの確認と管理
2. 圃場情報の提供
3. 農薬・肥料の使用指導（希釈倍率、使用制限）
4. 作業記録の管理
5. 作付け計画の支援
6. 作業提案と農薬ローテーション管理
7. 天候を考慮した作業計画

対応方針：
- 常に安全で正確な農業指導を心がけてください
- 農薬使用については、適切な希釈倍率と使用制限を確認してください
- 作業者のスキルレベルに応じて、分かりやすい指示を提供してください
- 不明な点については、適切な確認を促してください
- 作業完了の報告を受けた場合は、次回作業の自動スケジュールを提案してください

回答形式：
- LINEでの短いメッセージに適した簡潔な回答を心がけてください
- 重要な情報は箇条書きで整理してください
- 絵文字を適切に使用して、親しみやすい回答にしてください
- 農薬の希釈倍率や使用制限は必ず確認してください
"""

    def process_message(self, message: str, user_id: str) -> str:
        """ユーザーからのメッセージを処理し、応答を生成する"""
        if not self.agent_executor:
            logger.error("エージェントが初期化されていません。")
            return "申し訳ございません。システムの準備ができていません。少し待ってから再度お試しください。"

        try:
            response = self.agent_executor.invoke({"input": message, "user_id": user_id})

            if isinstance(response, dict) and "output" in response:
                return response["output"]
            return str(response)

        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
            return "申し訳ございません。処理中にエラーが発生しました。しばらくしてから再度お試しください。"


# グローバルエージェントインスタンス
agri_agent = AgriAIAgent()
