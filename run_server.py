"""
開発用サーバー起動スクリプト
"""

import logging
import uvicorn
from dotenv import load_dotenv
from src.agri_ai.core.config import setup_logging

# .envファイルから環境変数を読み込む
load_dotenv()

# ロギング設定
setup_logging()

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("農業AI LINE Bot Webhook サーバーを起動します...")
    uvicorn.run(
        "src.agri_ai.line_bot.webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None,  # カスタムロギング設定を使用するため、uvicornのデフォルトを無効化
    )
