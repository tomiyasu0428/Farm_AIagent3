"""
環境設定と設定値の管理
"""

import os
from typing import Optional
from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings


class GoogleAISettings(BaseModel):
    """Google AI API設定"""
    api_key: str = Field(default="", env="GOOGLE_API_KEY")
    model_name: str = Field(default="gemini-2.5-flash", env="GOOGLE_AI_MODEL")
    temperature: float = Field(default=0.1, env="GOOGLE_AI_TEMPERATURE")
    timeout: int = Field(default=30, env="AI_RESPONSE_TIMEOUT")


class MongoDBSettings(BaseModel):
    """MongoDB設定"""
    connection_string: str = Field(default="", env="MONGODB_CONNECTION_STRING")
    database_name: str = Field(default="agri_ai", env="MONGODB_DATABASE_NAME")
    max_pool_size: int = Field(default=50, env="MONGODB_MAX_POOL_SIZE")
    min_pool_size: int = Field(default=5, env="MONGODB_MIN_POOL_SIZE")
    connect_timeout: int = Field(default=10000, env="MONGODB_CONNECT_TIMEOUT")
    server_selection_timeout: int = Field(default=5000, env="MONGODB_SERVER_SELECTION_TIMEOUT")


class LINEBotSettings(BaseModel):
    """LINE Bot設定"""
    channel_access_token: str = Field(default="", env="LINE_CHANNEL_ACCESS_TOKEN")
    channel_secret: str = Field(default="", env="LINE_CHANNEL_SECRET")
    webhook_url: Optional[str] = Field(None, env="LINE_WEBHOOK_URL")


class GoogleCloudSettings(BaseModel):
    """Google Cloud設定"""
    project_id: Optional[str] = Field(None, env="GOOGLE_CLOUD_PROJECT")
    credentials_path: Optional[str] = Field(None, env="GOOGLE_APPLICATION_CREDENTIALS")


class AppSettings(BaseModel):
    """アプリケーション設定"""
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    max_concurrent_requests: int = Field(default=100, env="MAX_CONCURRENT_REQUESTS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")


class Settings(BaseSettings):
    """統合設定クラス"""
    
    model_config = {"env_file": ".env", "case_sensitive": False}
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_env_file()
        
        # 各設定グループを初期化
        self.google_ai = GoogleAISettings()
        self.mongodb = MongoDBSettings()
        self.line_bot = LINEBotSettings()
        self.google_cloud = GoogleCloudSettings()
        self.app = AppSettings()
    
    def _validate_env_file(self):
        """環境設定ファイルの検証"""
        env_file = ".env"
        if not os.path.exists(env_file):
            raise FileNotFoundError(
                f"環境設定ファイル '{env_file}' が見つかりません。"
                f"'.env.example' を '{env_file}' にコピーして適切な値を設定してください。"
            )
    
    # 後方互換性のためのプロパティ
    @property
    def google_api_key(self) -> str:
        return self.google_ai.api_key
    
    @property
    def mongodb_connection_string(self) -> str:
        return self.mongodb.connection_string
    
    @property
    def mongodb_database_name(self) -> str:
        return self.mongodb.database_name
    
    @property
    def line_channel_access_token(self) -> str:
        return self.line_bot.channel_access_token
    
    @property
    def line_channel_secret(self) -> str:
        return self.line_bot.channel_secret
    
    @property
    def environment(self) -> str:
        return self.app.environment
    
    @property
    def debug(self) -> bool:
        return self.app.debug
    
    @property
    def ai_response_timeout(self) -> int:
        return self.google_ai.timeout
    
    @property
    def max_concurrent_requests(self) -> int:
        return self.app.max_concurrent_requests


# グローバル設定インスタンス
settings = Settings()