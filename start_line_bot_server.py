#!/usr/bin/env python3
"""
LINE Bot Webhookサーバー起動スクリプト
"""

import uvicorn
import logging
from src.agri_ai.line_bot.webhook import app

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 LINE Bot Webhookサーバーを起動します...")
    logger.info("📍 サーバーアドレス: http://localhost:8000")
    logger.info("🔗 Webhook URL: http://localhost:8000/webhook")
    logger.info("🏥 ヘルスチェック: http://localhost:8000/health")
    logger.info("⚠️ ngrokを別ターミナルで起動してください: ngrok http 8000")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=False
        )
    except KeyboardInterrupt:
        logger.info("👋 サーバーを停止します...")
    except Exception as e:
        logger.error(f"❌ サーバー起動エラー: {e}")
        raise