"""
LangChainツールの基底クラス
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from langchain.tools import BaseTool
from pydantic import BaseModel
import logging

from ..database.mongodb_client import mongodb_client

logger = logging.getLogger(__name__)


class AgriAIBaseTool(BaseTool, ABC):
    """農業AI用基底ツールクラス"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mongodb_client = mongodb_client
    
    async def _get_collection(self, collection_name: str):
        """指定されたコレクションを取得"""
        return await self.mongodb_client.get_collection(collection_name)
    
    def _run(self, query: str, run_manager: Optional[Any] = None) -> str:
        """同期実行（非推奨）"""
        raise NotImplementedError("同期実行は非推奨です。_arunを使用してください。")
    
    async def _arun(self, query: str, run_manager: Optional[Any] = None) -> str:
        """非同期実行"""
        try:
            result = await self._execute(query)
            return self._format_result(result)
        except Exception as e:
            logger.error(f"ツール実行エラー ({self.name}): {e}")
            return f"エラーが発生しました: {str(e)}"
    
    @abstractmethod
    async def _execute(self, query: str) -> Any:
        """ツール固有の実行ロジック"""
        pass
    
    def _format_result(self, result: Any) -> str:
        """結果をLINEメッセージ用にフォーマット"""
        if isinstance(result, dict):
            return self._format_dict_result(result)
        elif isinstance(result, list):
            return self._format_list_result(result)
        else:
            return str(result)
    
    def _format_dict_result(self, result: Dict[str, Any]) -> str:
        """辞書形式の結果をフォーマット"""
        formatted_lines = []
        for key, value in result.items():
            formatted_lines.append(f"{key}: {value}")
        return "\n".join(formatted_lines)
    
    def _format_list_result(self, result: list) -> str:
        """リスト形式の結果をフォーマット"""
        if not result:
            return "結果がありません"
        
        formatted_lines = []
        for i, item in enumerate(result, 1):
            if isinstance(item, dict):
                item_str = self._format_dict_result(item)
            else:
                item_str = str(item)
            formatted_lines.append(f"{i}. {item_str}")
        
        return "\n".join(formatted_lines)