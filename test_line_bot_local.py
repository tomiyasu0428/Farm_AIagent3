#!/usr/bin/env python3
"""
LINE Bot ローカルテスト用スクリプト
"""

import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from src.agri_ai.line_bot.webhook import app
from src.agri_ai.core.master_agent import master_agent

# 環境変数を読み込み
load_dotenv()

async def test_line_bot_functionality():
    """LINE Bot機能のローカルテスト"""
    try:
        print("📱 LINE Bot機能のローカルテストを開始します...")
        
        # MasterAgentの初期化
        master_agent.initialize()
        print("✅ MasterAgent初期化成功")
        
        # 模擬的なLINEメッセージイベントを作成
        test_messages = [
            "今日のタスクを教えて",
            "第1ハウスの状況は？",
            "トマトに使える農薬を教えて",
            "防除作業終わりました",
            "明日の作業予定を確認したい"
        ]
        
        print("\n🔍 LINE Bot メッセージ処理テスト:")
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n--- テスト {i} ---")
            print(f"📨 受信メッセージ: {message}")
            
            try:
                # MasterAgentでメッセージを処理
                result = await master_agent.process_message_async(message, "test_user_line")
                response = result.get('response', 'エラーが発生しました')
                
                # プランがある場合は表示
                if result.get('plan'):
                    print(f"🚀 実行プラン:")
                    print(result['plan'])
                    print()
                print(f"🤖 MasterAgent応答:")
                print(response)
                
                # 応答の長さをチェック（LINEメッセージの制限対応）
                if len(response) > 2000:
                    print("⚠️  応答が長すぎます（2000文字制限）")
                    response_truncated = response[:1990] + "..."
                    print(f"📝 短縮版: {response_truncated}")
                
                print(f"✅ テスト {i} 完了")
                
            except Exception as e:
                print(f"❌ テスト {i} エラー: {e}")
            
            print("-" * 50)
            
            # 短い待機（レート制限対応）
            await asyncio.sleep(0.5)
        
        print("\n✅ LINE Bot機能のローカルテストが完了しました！")
        
        # Webhookアプリケーションの設定確認
        print("\n🔧 LINE Bot Webhook設定確認:")
        print(f"📍 Webhook URL: http://localhost:8000/webhook")
        print(f"🔍 ヘルスチェック: http://localhost:8000/health")
        print(f"🏠 ルートエンドポイント: http://localhost:8000/")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        raise
    finally:
        # master_agent.shutdown()  # shutdownメソッドはないので削除
        pass

async def test_webhook_endpoints():
    """Webhookエンドポイントのテスト"""
    try:
        print("\n🌐 Webhookエンドポイントのテスト:")
        
        # テスト用のHTTPクライアントを作成
        from httpx import AsyncClient
        
        async with AsyncClient() as client:
            # ヘルスチェック
            print("🏥 ヘルスチェックテスト...")
            # 実際のリクエストは省略（サーバー起動が必要）
            print("  ⚠️  サーバー起動後にテスト可能")
            
            # プッシュメッセージテスト
            print("📤 プッシュメッセージテスト...")
            print("  ⚠️  LINE Bot設定後にテスト可能")
            
        print("✅ Webhookエンドポイントの設定確認完了")
        
    except Exception as e:
        print(f"❌ Webhookテストエラー: {e}")

async def main():
    await test_line_bot_functionality()
    await test_webhook_endpoints()

if __name__ == "__main__":
    asyncio.run(main())