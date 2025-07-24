"""
FieldAgent: 圃場情報専門エージェント

AIエージェント構築のポイントに基づく設計:
- 単一責任: 圃場情報のみに特化
- ツール削除なし: FieldInfoToolのみを保持
- KV-Cache最適化: 一貫したプロンプト構造
"""

import logging
from typing import Any, Dict, List, Optional

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.agents.format_scratchpad import format_to_tool_messages
from langchain.agents.output_parsers import ToolsAgentOutputParser
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from ..langchain_tools.field_info_tool import FieldInfoTool
from ..core.config import settings

logger = logging.getLogger(__name__)


class FieldAgent:
    """
    圃場情報専門エージェント
    
    責任範囲:
    - 圃場の基本情報（名前、面積、土壌タイプ）
    - 現在の作付け状況（作物、品種、生育段階）
    - 作付け計画との連携
    - 次回作業予定の確認
    """
    
    def __init__(self):
        """FieldAgentの初期化"""
        self.config = settings
        self.llm = self._setup_llm()
        self.tools = self._setup_tools()
        self.agent_executor = self._create_agent()
        
    def _setup_llm(self) -> ChatGoogleGenerativeAI:
        """LLMの設定"""
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=self.config.google_ai.api_key,
            temperature=0.1,
            max_tokens=2048,
            timeout=30
        )
    
    def _setup_tools(self) -> List[Any]:
        """ツールの設定 - 圃場情報取得専用"""
        return [
            FieldInfoTool(),           # 圃場情報取得
        ]
    
    def _create_system_prompt(self) -> str:
        """
        KV-Cache最適化された固定システムプロンプト
        AIエージェント構築のポイント: プロンプト構造の安定化
        """
        return """あなたは圃場情報の専門家「FieldAgent」です。

## 専門領域
圃場（畑やハウス）に関する情報の検索・取得を担当します。

## 主要機能
### 圃場情報の検索・取得 ⭐ 
- 圃場の基本情報（名前、面積、土壌タイプ）
- 現在の作付け状況（作物、品種、生育段階）
- 作付け計画の確認
- 次回作業予定の情報
- エリア別圃場一覧
- 複数圃場の一括表示

## 応答方針
1. 正確で詳細な圃場情報を提供する
2. 数値データは正確に伝える
3. 見つからない圃場は明確に報告する
4. 複数圃場は整理して表示する
5. 圃場登録要求は対応範囲外（専門エージェントを案内）

## 利用可能ツール
- field_info: 圃場情報の取得・検索

圃場の情報検索について、何でもお聞きください！
※圃場の新規登録は専門の登録エージェントが担当します。"""

    def _create_agent(self) -> AgentExecutor:
        """エージェントの作成"""
        # プロンプトテンプレートの作成（KV-Cache最適化）
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._create_system_prompt()),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # ツール呼び出しエージェントの作成
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # エージェント実行器の作成
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate",
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )
    
    async def process_query(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """
        圃場関連クエリの処理
        
        Args:
            query: ユーザーからの質問
            chat_history: 会話履歴（オプション）
            
        Returns:
            処理結果辞書
        """
        try:
            logger.info(f"FieldAgent処理開始: {query}")
            
            # 圃場情報関連かどうかの事前チェック
            if not self._is_field_info_query(query):
                if self._is_registration_query(query):
                    return {
                        "success": False,
                        "response": "圃場の新規登録については、専門の登録エージェントが担当いたします。MasterAgentを通じて登録をご依頼ください。",
                        "agent_type": "field_agent",
                        "query_type": "registration_redirect"
                    }
                else:
                    return {
                        "success": False,
                        "response": "申し訳ございませんが、圃場情報の検索以外のご質問には対応できません。圃場の名前、面積、作付け状況などについてお聞きください。",
                        "agent_type": "field_agent",
                        "query_type": "out_of_scope"
                    }
            
            # エージェント実行
            result = await self.agent_executor.ainvoke({
                "input": query,
                "chat_history": chat_history or []
            })
            
            return {
                "success": True,
                "response": result["output"],
                "agent_type": "field_agent",
                "query_type": "field_info",
                "intermediate_steps": result.get("intermediate_steps", [])
            }
            
        except Exception as e:
            logger.error(f"FieldAgent処理エラー: {e}")
            return {
                "success": False,
                "response": f"圃場情報の取得中にエラーが発生しました: {str(e)}",
                "agent_type": "field_agent",
                "error": str(e)
            }
    
    def _is_field_info_query(self, query: str) -> bool:
        """
        圃場情報検索クエリかどうかの判定
        
        Args:
            query: ユーザークエリ
            
        Returns:
            圃場情報検索かどうか
        """
        field_info_keywords = [
            # 圃場関連基本キーワード
            "圃場", "ハウス", "畑", "田", "フィールド",
            "A畑", "B畑", "C畑", "第1", "第2", "第3",
            "面積", "土壌", "作付け", "栽培", "生育",
            "全圃場", "すべて", "一覧", "状況", "情報",
            "確認", "教えて", "どこ", "何",
            
            # エリア関連（検索文脈で）
            "エリア", "地区", "豊糠", "豊緑",
            
            # 固有圃場名キーワード
            "橋向こう", "登山道前", "橋前", "田んぼあと",
            "若菜横", "学校裏", "相田さん向かい", "フォレスト",
            "学校前", "新田", "若菜裏"
        ]
        
        # 登録キーワードが含まれていない場合のみ情報検索とみなす
        registration_keywords = ["登録", "追加", "新しい", "作成", "新規"]
        has_registration = any(keyword in query for keyword in registration_keywords)
        has_field_info = any(keyword in query for keyword in field_info_keywords)
        
        return has_field_info and not has_registration
    
    def _is_registration_query(self, query: str) -> bool:
        """
        圃場登録クエリかどうかの判定
        
        Args:
            query: ユーザークエリ
            
        Returns:
            圃場登録かどうか
        """
        registration_keywords = ["登録", "追加", "新しい", "作成", "新規"]
        field_keywords = ["圃場", "ハウス", "畑", "田", "フィールド"]
        
        has_registration = any(keyword in query for keyword in registration_keywords)
        has_field = any(keyword in query for keyword in field_keywords)
        
        return has_registration and has_field
    
    def get_capabilities(self) -> Dict[str, Any]:
        """エージェントの能力情報を返す"""
        return {
            "agent_name": "FieldAgent",
            "specialization": "圃場情報検索",
            "tools": ["field_info"],
            "supported_queries": [
                "圃場の基本情報確認",
                "現在の作付け状況",
                "作付け計画の確認", 
                "次回作業予定の確認",
                "エリア別圃場一覧"
            ],
            "sample_queries": [
                "第1ハウスの状況を教えて",
                "A畑の面積はどのくらい？",
                "全圃場の作付け状況を確認",
                "現在育てている作物は何？",
                "豊緑エリアの圃場一覧"
            ],
            "architecture_benefit": "単一責任によるイベントループ安定化"
        }


# 使用例とテスト用の関数
async def test_field_agent():
    """FieldAgentのテスト実行"""
    agent = FieldAgent()
    
    test_queries = [
        "第1ハウスの状況を教えて",
        "全圃場の状況を確認したい",
        "A畑の面積は？",
        "今日の天気は？"  # 対応範囲外のテスト
    ]
    
    for query in test_queries:
        print(f"\n--- テスト: {query} ---")
        result = await agent.process_query(query)
        print(f"成功: {result['success']}")
        print(f"応答: {result['response']}")
        print(f"タイプ: {result.get('query_type', 'unknown')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_field_agent())