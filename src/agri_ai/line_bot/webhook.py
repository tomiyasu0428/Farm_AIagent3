"""
LINE Bot Webhook実装
"""

import hashlib
import hmac
import base64
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import logging
import concurrent.futures

from ..core.config import settings
from ..core.agent import agri_agent

logger = logging.getLogger(__name__)

# FastAPIアプリケーションの作成
app = FastAPI(title="農業AI LINE Webhook", version="1.0.0")

# LINE Bot APIの初期化
line_bot_api = LineBotApi(settings.line_channel_access_token)
handler = WebhookHandler(settings.line_channel_secret)


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {"message": "Agri AI LINE Bot Webhook is running."}


@app.get("/health")
async def health_check():
    """詳細なヘルスチェック"""
    try:
        # MongoDB接続チェック
        from ..database.mongodb_client import mongodb_client

        db_health = await mongodb_client.health_check()

        return {
            "status": "healthy",
            "database": db_health,
            "agent": "initialized" if agri_agent.agent_executor else "not_initialized",
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.post("/webhook")
async def webhook(request: Request):
    """LINE Webhookエンドポイント"""
    try:
        # リクエストボディの取得
        body = await request.body()

        # 署名の検証
        signature = request.headers.get("X-Line-Signature", "")
        if not _verify_signature(body, signature):
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Webhookの処理
        try:
            handler.handle(body.decode("utf-8"), signature)
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        except LineBotApiError as e:
            logger.error(f"LINE Bot API エラー: {e}")
            raise HTTPException(status_code=500, detail="LINE Bot API error")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Webhook処理エラー: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _verify_signature(body: bytes, signature: str) -> bool:
    """署名の検証"""
    try:
        hash_value = hmac.new(settings.line_channel_secret.encode("utf-8"), body, hashlib.sha256).digest()

        signature_hash = base64.b64encode(hash_value).decode("utf-8")
        return hmac.compare_digest(signature, signature_hash)
    except Exception as e:
        logger.error(f"署名検証エラー: {e}")
        return False


def _process_message_sync(message_text: str, user_id: str, reply_token: str):
    """同期的にメッセージを処理する関数"""
    try:
        # エージェントが初期化されているか確認
        if not agri_agent.agent_executor:
            logger.info("エージェントが初期化されていません。初回リクエストのため初期化します。")
            agri_agent.initialize()

        logger.info(f"メッセージ処理開始 - ユーザー: {user_id}, 内容: {message_text}")

        # エージェントでメッセージを処理
        ai_response = agri_agent.process_message(message_text, user_id)
        logger.info(f"AI応答生成完了 - ユーザー: {user_id}")

        # 応答メッセージの送信
        line_bot_api.reply_message(reply_token, TextSendMessage(text=ai_response))
        logger.info(f"応答送信完了 - ユーザー: {user_id}")

    except Exception as e:
        logger.error(f"メッセージ処理エラー - ユーザー: {user_id}, エラー: {e}")
        # エラー時の応答
        try:
            line_bot_api.reply_message(
                reply_token, TextSendMessage(text="申し訳ございません。処理中にエラーが発生しました。")
            )
        except Exception as reply_error:
            logger.error(f"エラー応答送信失敗: {reply_error}")


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """テキストメッセージの処理"""
    try:
        user_id = event.source.user_id
        message_text = event.message.text
        reply_token = event.reply_token

        logger.info(f"受信メッセージ - ユーザー: {user_id}, 内容: {message_text}")

        # 別スレッドで処理を実行（FastAPIのイベントループと競合しないように）
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_process_message_sync, message_text, user_id, reply_token)
            future.result(timeout=30)  # 30秒でタイムアウト

    except concurrent.futures.TimeoutError:
        logger.error("メッセージ処理がタイムアウトしました")
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="処理に時間がかかっています。しばらくしてから再度お試しください。"),
            )
        except Exception as reply_error:
            logger.error(f"タイムアウト応答送信失敗: {reply_error}")

    except Exception as e:
        logger.error(f"メッセージハンドラーエラー: {e}")
        # エラー時の応答
        try:
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text="申し訳ございません。処理中にエラーが発生しました。")
            )
        except Exception as reply_error:
            logger.error(f"エラー応答送信失敗: {reply_error}")


@app.post("/push")
async def push_message(data: Dict[str, Any]):
    """プッシュメッセージの送信（開発・テスト用）"""
    try:
        user_id = data.get("user_id")
        message = data.get("message")

        if not user_id or not message:
            raise HTTPException(status_code=400, detail="user_id and message are required")

        line_bot_api.push_message(user_id, TextSendMessage(text=message))

        return {"status": "sent", "user_id": user_id, "message": message}

    except Exception as e:
        logger.error(f"プッシュメッセージ送信エラー: {e}")
        raise HTTPException(status_code=500, detail="Failed to send push message")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
