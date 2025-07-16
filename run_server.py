"""
開発用サーバー起動スクリプト
"""

import uvicorn
import logging
from src.agri_ai.core.config import settings

# ログ設定
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("農業AI LINE Bot Webhook サーバーを起動します...")
    
    # 開発用サーバーの起動
    uvicorn.run(
        "src.agri_ai.line_bot.webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )