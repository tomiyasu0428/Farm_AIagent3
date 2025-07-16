"""
環境設定と設定値の管理
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    # 環境設定
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # OpenAI API設定
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # MongoDB設定
    mongodb_connection_string: str = Field(..., env="MONGODB_CONNECTION_STRING")
    mongodb_database_name: str = Field(default="agri_ai", env="MONGODB_DATABASE_NAME")
    
    # LINE Bot設定
    line_channel_access_token: str = Field(..., env="LINE_CHANNEL_ACCESS_TOKEN")
    line_channel_secret: str = Field(..., env="LINE_CHANNEL_SECRET")
    
    # Google Cloud設定
    google_cloud_project: Optional[str] = Field(None, env="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")
    
    # パフォーマンス設定
    ai_response_timeout: int = Field(default=30, env="AI_RESPONSE_TIMEOUT")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    
    model_config = {"env_file": ".env", "case_sensitive": False}


# グローバル設定インスタンス
settings = Settings()