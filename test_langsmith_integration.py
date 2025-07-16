"""
LangSmith トレーシング機能のテスト
"""

import asyncio
import logging
import os
from src.agri_ai.core.agent import agri_agent
from src.agri_ai.core.config import settings

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_langsmith_integration():
    """LangSmith統合のテスト"""
    try:
        # 環境変数の確認
        print("=== 環境変数の確認 ===")
        print(f"LANGSMITH_API_KEY: {'設定済み' if settings.langsmith.api_key else '未設定'}")
        print(f"LANGSMITH_PROJECT: {settings.langsmith.project_name}")
        print(f"LANGSMITH_TRACING: {settings.langsmith.tracing_enabled}")
        print(f"LANGSMITH_ENDPOINT: {settings.langsmith.endpoint}")
        print()

        # 環境変数の表示（LangChain用）
        print("=== LangChain環境変数 ===")
        print(f"LANGCHAIN_TRACING_V2: {os.environ.get('LANGCHAIN_TRACING_V2', '未設定')}")
        print(f"LANGCHAIN_API_KEY: {'設定済み' if os.environ.get('LANGCHAIN_API_KEY') else '未設定'}")
        print(f"LANGCHAIN_PROJECT: {os.environ.get('LANGCHAIN_PROJECT', '未設定')}")
        print(f"LANGCHAIN_ENDPOINT: {os.environ.get('LANGCHAIN_ENDPOINT', '未設定')}")
        print()

        # エージェントの初期化
        print("=== エージェント初期化 ===")
        await agri_agent.initialize()
        print("エージェント初期化完了")
        print()

        # テストメッセージの送信
        test_messages = [
            "今日のタスクを教えて",
            "ブロッコリーの育て方について教えて",
            "農薬の希釈倍率を教えて",
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"=== テスト {i}: {message} ===")
            response = await agri_agent.process_message(message, "test_user_123")
            print(f"応答: {response}")
            print()

        # エージェントの終了
        print("=== エージェント終了 ===")
        await agri_agent.shutdown()
        print("エージェント終了完了")

        print("\n✅ LangSmithトレーシングテスト完了!")
        if settings.langsmith.tracing_enabled:
            print(f"🔍 LangSmithダッシュボードで実行ログを確認してください: {settings.langsmith.endpoint}")
            print(f"📂 プロジェクト: {settings.langsmith.project_name}")
        else:
            print("⚠️  LangSmithトレーシングが無効になっています")
            print("   LANGSMITH_TRACING=true と LANGSMITH_API_KEY を設定してトレーシングを有効にしてください")

    except Exception as e:
        logger.error(f"テストエラー: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_langsmith_integration())
