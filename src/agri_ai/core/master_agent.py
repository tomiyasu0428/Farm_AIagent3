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
from ..langchain_tools.task_lookup_tool import TaskLookupTool
from ..langchain_tools.task_update_tool import TaskUpdateTool
from ..langchain_tools.field_info_tool import FieldInfoTool
from ..langchain_tools.crop_material_tool import CropMaterialTool
from ..langchain_tools.work_suggestion_tool import WorkSuggestionTool
from ..database.mongodb_client import mongodb_client

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
            TaskLookupTool(),
            TaskUpdateTool(),
            FieldInfoTool(),  # 既存ツール維持（互換性のため）
            CropMaterialTool(),
            WorkSuggestionTool(),
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
1. task_lookup: 今日のタスクや作業予定を検索
2. task_update: 作業の完了報告や延期処理
3. field_info: 圃場の詳細情報や作付け状況を取得
4. crop_material: 作物と資材の対応関係、希釈倍率を検索
5. work_suggestion: 作業提案、農薬ローテーション、天候を考慮した作業計画
6. field_agent_tool: 圃場情報専門エージェント（情報取得・検索）
7. field_registration_agent_tool: 圃場登録専門エージェント（新規登録・追加）

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
1. 作業タスクの確認と管理
2. 圃場情報の提供と登録管理
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
            # 1. 実行プランの作成（非同期対応）
            plan = await self._create_execution_plan(message)
            
            # 2. エージェント実行
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
    
    async def _create_execution_plan(self, message: str) -> str:
        """
        実行プランの作成（動的圃場名抽出対応）
        AIエージェント構築のポイント: プラン共有機能
        """
        # より具体的なプラン生成ロジック
        if any(keyword in message for keyword in ["登録", "追加", "新しい", "作成"]) and any(keyword in message for keyword in ["圃場", "ハウス", "畑"]):
            # 圃場名を動的に抽出してプランに含める
            field_name = await self._extract_field_name(message)
            if field_name:
                return f"📋 実行プラン\n1. 「{field_name}」を新規圃場として登録処理\n2. 面積・エリア情報を含めてデータベースに保存\n3. 登録完了通知をユーザーに送信"
            else:
                return "📋 実行プラン\n1. 圃場登録専門エージェント(FieldRegistrationAgent)で新しい圃場を登録\n2. 登録結果を確認してユーザーに報告"
        elif any(keyword in message for keyword in ["圃場", "ハウス", "畑", "面積", "作付け"]):
            # 圃場名や具体的な情報を動的に抽出
            field_name = await self._extract_field_name(message)
            if field_name:
                if "面積" in message:
                    return f"📋 実行プラン\n1. 「{field_name}」の面積情報をリサーチ\n2. 結果をha単位でユーザーにレポート"
                elif "一覧" in message or "すべて" in message:
                    area_name = self._extract_area_name(message)
                    if area_name:
                        return f"📋 実行プラン\n1. 「{area_name}」の圃場一覧をリサーチ\n2. 各圃場の面積・作付け状況をユーザーにレポート"
                    else:
                        return "📋 実行プラン\n1. 全圃場の一覧情報をリサーチ\n2. 面積・作付け状況を整理してユーザーにレポート"
                else:
                    return f"📋 実行プラン\n1. 「{field_name}」の詳細情報をリサーチ\n2. 面積・作付け・作業予定をユーザーにレポート"
            else:
                return "📋 実行プラン\n1. 圃場情報を専門エージェント(FieldAgent)で調査\n2. 結果をわかりやすく整理して報告"
        elif any(keyword in message for keyword in ["タスク", "作業", "予定"]):
            return "📋 実行プラン\n1. 今日の作業タスクをデータベースから検索\n2. 見つかったタスクの詳細をユーザーにレポート"
        elif any(keyword in message for keyword in ["農薬", "資材", "希釈"]):
            material_name = self._extract_material_name(message)
            if material_name:
                return f"📋 実行プラン\n1. 「{material_name}」の使用方法・希釈倍率をリサーチ\n2. 安全な使用指導をユーザーにレポート"
            else:
                return "📋 実行プラン\n1. 資材データベースから対象情報を検索\n2. 安全な使用方法と注意事項を確認\n3. 詳細情報を報告"
        else:
            query_type = self._analyze_query_type(message)
            return f"📋 実行プラン\n1. 「{query_type}」について最適なツールで情報収集\n2. 結果を整理してユーザーにレポート"

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

    async def _extract_field_name(self, message: str) -> str:
        """メッセージから圃場名を動的に抽出"""
        try:
            from ..services.field_name_extractor import FieldNameExtractor
            
            extractor = FieldNameExtractor()
            result = await extractor.extract_field_name(message)
            
            # 信頼度が50%以上の場合のみ採用
            if result['confidence'] >= 0.5:
                logger.info(f"動的圃場名抽出成功: {result['field_name']} (信頼度: {result['confidence']:.2f})")
                return result['field_name']
            else:
                logger.info(f"動的圃場名抽出: 信頼度不足 ({result['confidence']:.2f})")
                return ""
                
        except Exception as e:
            logger.error(f"動的圃場名抽出エラー: {e}")
            # フォールバック: 従来の正規表現方式
            return self._extract_field_name_fallback(message)
    
    def _extract_field_name_fallback(self, message: str) -> str:
        """フォールバック用の従来圃場名抽出"""
        import re
        
        # 改良された正規表現パターン
        field_patterns = [
            r'「([^」]+)」',           # 「圃場名」
            r'([^のを\s]{2,})の(?:面積|情報|詳細|状況)',  # 2文字以上の圃場名
            r'([^のを\s]{2,})を(?:登録|追加)',         # 2文字以上の圃場名
            r'([^のを\s]{2,})は(?:どこ|何)',           # 2文字以上の圃場名
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, message)
            if match:
                extracted = match.group(1)
                if len(extracted) >= 2:  # 最小長チェック
                    return extracted
        
        return ""

    def _extract_area_name(self, message: str) -> str:
        """メッセージからエリア名を抽出"""
        if "豊糠" in message:
            return "豊糠エリア"
        elif "豊緑" in message:
            return "豊緑エリア"
        return ""

    def _extract_material_name(self, message: str) -> str:
        """メッセージから資材名を抽出"""
        import re
        
        # 資材名のパターン
        material_patterns = [
            r'「([^」]+)」',  # 「農薬名」
            r'([^の\s]+)の希釈',  # 農薬名の希釈
            r'([^を\s]+)を',     # 農薬名を
        ]
        
        for pattern in material_patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        
        return ""

    def _analyze_query_type(self, message: str) -> str:
        """クエリタイプを分析"""
        if any(keyword in message for keyword in ["天気", "気温", "雨"]):
            return "天気情報"
        elif any(keyword in message for keyword in ["病気", "害虫", "症状"]):
            return "病害虫診断"
        elif any(keyword in message for keyword in ["収穫", "出荷", "販売"]):
            return "収穫・出荷情報"
        else:
            return "農業全般の問い合わせ"


# グローバルエージェントインスタンス
master_agent = MasterAgent()
