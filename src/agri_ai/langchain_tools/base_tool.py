"""
LangChainツールの基底クラス
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from langchain.tools import BaseTool
import logging
from pydantic import Field

from ..database.mongodb_client import mongodb_client

logger = logging.getLogger(__name__)


class AgriAIBaseTool(BaseTool, ABC):
    """農業AI用基底ツールクラス"""

    # mongodb_clientフィールドを明示的に宣言
    mongodb_client: Any = Field(default=None, exclude=True)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, mongodb_client_instance=None, **kwargs):
        # mongodb_client を明示的に設定
        if mongodb_client_instance is not None:
            kwargs["mongodb_client"] = mongodb_client_instance
        else:
            kwargs.setdefault("mongodb_client", mongodb_client)
        super().__init__(**kwargs)

    async def _get_collection(self, collection_name: str):
        """指定されたコレクションを取得"""
        return await self.mongodb_client.get_collection(collection_name)

    def _run(self, query: str, run_manager: Optional[Any] = None) -> str:
        """同期実行（非同期メソッドをラップ）"""
        import asyncio

        try:
            # 現在のイベントループの状態を確認
            try:
                asyncio.get_running_loop()
                # 実行中のループがある場合は、ThreadPoolExecutorで新しいスレッドで実行
                import concurrent.futures

                def run_async():
                    # 新しいイベントループを作成
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._arun(query, run_manager))
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    return future.result()

            except RuntimeError:
                # イベントループが実行中でない場合は直接実行
                return asyncio.run(self._arun(query, run_manager))

        except Exception as e:
            logger.error(f"同期実行エラー: {e}")
            return f"ツール実行エラーが発生しました: {str(e)}"

    async def _execute_sync(self, query: str) -> Any:
        """非同期実行のラッパー"""
        return await self._execute(query)

    @abstractmethod
    async def _arun(self, query: str, run_manager: Optional[Any] = None) -> str:
        """非同期実行（サブクラスで実装）"""
        raise NotImplementedError("サブクラスで実装してください")

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

    def _format_dict_result(self, result: dict) -> str:
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
