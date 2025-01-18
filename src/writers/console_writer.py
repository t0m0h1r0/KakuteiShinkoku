from typing import List, Any
import logging

from .base import BaseWriter

class ConsoleWriter(BaseWriter):
    """コンソール出力クラス"""
    
    def __init__(self):
        # コンソール出力のため、出力パスは不要
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def write(self, records: List[Any]) -> None:
        """レコードをコンソールに出力"""
        if not records:
            self._logger.warning("No records to display")
            return
        
        # サマリーの出力を完全に削除

    def _format_record(self, record: Any) -> str:
        """レコードを文字列にフォーマット"""
        try:
            # 辞書形式でない場合は文字列に変換
            return str(record)
        except Exception:
            return str(record)