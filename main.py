"""
農業AI エージェント - メインアプリケーション
"""

import asyncio
import logging
from src.agri_ai.line_bot.webhook import app
from src.agri_ai.core.config import settings

# ログ設定
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agri_ai.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """メイン関数"""
    try:
        logger.info("農業AI エージェントを起動しています...")
        logger.info(f"環境: {settings.environment}")
        logger.info(f"デバッグモード: {settings.debug}")
        
        # 設定の検証
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEYが設定されていません")
        
        if not settings.mongodb_connection_string:
            raise ValueError("MONGODB_CONNECTION_STRINGが設定されていません")
        
        if not settings.line_channel_access_token:
            raise ValueError("LINE_CHANNEL_ACCESS_TOKENが設定されていません")
        
        logger.info("設定の検証が完了しました")
        
        # アプリケーションの起動はuvicornで行う
        logger.info("アプリケーションが正常に起動しました")
        
    except Exception as e:
        logger.error(f"起動エラー: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())