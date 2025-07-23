#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ローカル環境でエージェントを直接テストするスクリプト
"""

import asyncio
import logging
from src.agri_ai.core.agent import AgriAIAgent
from src.agri_ai.core.config import AgriAIConfig

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger(__name__)


async def test_agent():
    """エージェントをローカルでテストする"""
    try:
        print("🚀 農業AIエージェントを初期化しています...")

        # 設定を読み込み
        config = AgriAIConfig()

        # エージェントを初期化
        agent = AgriAIAgent(config)
        await agent.initialize()

        print("✅ エージェントの初期化が完了しました！")
        print("📝 質問を入力してください（'quit'で終了）:")

        while True:
            user_input = input("\n👤 あなた: ").strip()

            if user_input.lower() in ["quit", "exit", "終了", "やめる"]:
                print("👋 テストを終了します。")
                break

            if not user_input:
                continue

            print("🤖 エージェント: 考え中...")

            try:
                # エージェントに質問を投げる
                response = await agent.process_message(user_input)
                print(f"🤖 エージェント: {response}")

            except Exception as e:
                logger.error(f"メッセージ処理エラー: {e}")
                print(f"❌ エラーが発生しました: {e}")

    except Exception as e:
        logger.error(f"エージェント初期化エラー: {e}")
        print(f"❌ 初期化に失敗しました: {e}")


def main():
    """メイン関数"""
    print("🌾 農業AIエージェント ローカルテスト")
    print("=" * 50)

    try:
        asyncio.run(test_agent())
    except KeyboardInterrupt:
        print("\n👋 テストを中断しました。")
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        print(f"❌ 実行中にエラーが発生しました: {e}")


if __name__ == "__main__":
    main()
