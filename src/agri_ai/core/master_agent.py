"""
MasterAgent: 農業AI司令塔エージェント

AIエージェント構築のポイントに基づく設計:
- KV-Cache最適化: 固定システムプロンプト
- プラン共有: 処理の透明性確保
- 専門エージェント連携: FieldAgentなどの専門家を管理
"""

import os

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

from .config import settings
from ..database.mongodb_client import mongodb_client
from ..services.query_analyzer import QueryAnalyzer

logger = logging.getLogger(__name__)


class MasterAgent:
    """
    農業AI司令塔エージェント
    
    役割:
    - ユーザー指示の解釈と分析
    - 適切な専門エージェントへのタスク委譲
    - 実行プランの作成と共有
    - 統合的な結果の提供
    """

    def __init__(self):
        self.llm = None
        self.agent_executor = None
        self.tools = []
        self.field_agent = None  # 圃場専門エージェント
        self.execution_plan = None  # 実行プラン
        self.query_analyzer = QueryAnalyzer()  # クエリ分析サービス

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
        # MongoDB接続は非同期処理で実行
        import asyncio

        if not mongodb_client.is_connected:
            try:
                # 既存のイベントループを確認
                try:
                    loop = asyncio.get_running_loop()
                    # 既にイベントループが実行中の場合はタスクとしてスケジュール
                    task = loop.create_task(mongodb_client.connect())
                    # メッセージ処理前に接続完了を待つ
                    logger.info("MongoDB接続タスクをスケジュールしました")
                except RuntimeError:
                    # イベントループが実行されていない場合は同期実行
                    asyncio.run(mongodb_client.connect())
            except Exception as e:
                logger.error(f"MongoDB接続エラー: {e}")
                raise

        # 専門エージェントの初期化
        self._initialize_specialized_agents()
        
        # ツールの初期化
        self._initialize_tools()

        # LLMの初期化
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.1, google_api_key=settings.google_ai.api_key
        )

        # エージェントの作成
        self._initialize_agent()
        logger.info("農業AIエージェントの初期化が完了しました")

    def _initialize_specialized_agents(self):
        """専門エージェントの初期化"""
        from ..agents.field_agent import FieldAgent
        from ..agents.field_registration_agent import FieldRegistrationAgent
        
        self.field_agent = FieldAgent()
        self.field_registration_agent = FieldRegistrationAgent()
        logger.info("専門エージェント初期化完了")
    
    def _initialize_tools(self):
        """ツールの初期化（AIエージェント構築のポイント: ツール削除なし）"""
        from ..langchain_tools.field_agent_tool import FieldAgentTool
        from ..langchain_tools.field_registration_agent_tool import FieldRegistrationAgentTool
        
        self.tools = [
            FieldAgentTool(self.field_agent),  # 圃場情報専門エージェント
            FieldRegistrationAgentTool(self.field_registration_agent),  # 圃場登録専門エージェント
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
1. field_agent_tool: 圃場情報専門エージェント（情報取得・検索）
2. field_registration_agent_tool: 圃場登録専門エージェント（新規登録・追加）

専門エージェント連携：
- FieldAgent: 圃場情報の専門家
  - 圃場の検索・情報取得
  - エリア別圃場管理
  - 作付け状況の管理
- FieldRegistrationAgent: 圃場登録の専門家
  - 新しい圃場の登録・追加
  - エリア別圃場作成
  - 圃場データの検証

主な責務：
司令塔として適切な専門エージェントに作業を振り分けること

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

    async def process_message_async(self, message: str, user_id: str) -> dict:
        """
        非同期でユーザーからのメッセージを処理し、応答を生成する
        
        Returns:
            dict: {
                'response': str,      # ユーザーへの応答
                'plan': str,          # 実行プラン（オプション）
                'agent_used': str     # 使用したエージェント
            }
        """
        if not self.agent_executor:
            logger.error("エージェントが初期化されていません。")
            return {
                'response': "申し訳ございません。システムの準備ができていません。少し待ってから再度お試しください。",
                'agent_used': 'master_agent',
                'error': True
            }

        # MongoDB接続確認
        if not mongodb_client.is_connected:
            try:
                await mongodb_client.connect()
            except Exception as e:
                logger.error(f"MongoDB接続エラー: {e}")
                return {
                    'response': "データベース接続エラーが発生しました。しばらくしてから再度お試しください。",
                    'agent_used': 'master_agent',
                    'error': True
                }

        try:
            # 1. クエリ分析
            analysis_result = await self.query_analyzer.analyze_query_intent(message)
            
            # 2. 実行プランの作成
            plan = await self.query_analyzer.create_execution_plan(analysis_result)
            
            # 3. エージェント実行
            response = self.agent_executor.invoke({"input": message, "user_id": user_id})

            if isinstance(response, dict) and "output" in response:
                final_response = response["output"]
            else:
                final_response = str(response)
                
            return {
                'response': final_response,
                'plan': plan,
                'agent_used': 'master_agent'
            }

        except Exception as e:
            logger.error(f"メッセージ処理エラー: {e}")
            return {
                'response': "申し訳ございません。処理中にエラーが発生しました。しばらくしてから再度お試しください。",
                'agent_used': 'master_agent',
                'error': True
            }

    def process_message(self, message: str, user_id: str) -> str:
        """同期ラッパー関数（後方互換性のため）"""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            # 既にイベントループが実行中の場合は同期実行できない
            logger.warning("イベントループ実行中のため、同期実行はできません")
            return "システムが処理中です。しばらくお待ちください。"
        except RuntimeError:
            # イベントループが実行されていない場合は非同期実行結果を取得
            result = asyncio.run(self.process_message_async(message, user_id))
            return result.get('response', 'エラーが発生しました')


# グローバルエージェントインスタンス
master_agent = MasterAgent()
