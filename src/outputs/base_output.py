from abc import ABC, abstractmethod
from typing import Any, Optional
import logging
from ..formatters.base_formatter import BaseFormatter

class BaseOutput(ABC):
    """出力処理の基底クラス"""
    
    def __init__(self, formatter: Optional[BaseFormatter] = None):
        self.formatter = formatter
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def output(self, data: Any) -> None:
        """データを出力する抽象メソッド"""
        pass

    def _format_data(self, data: Any) -> str:
        """データをフォーマット"""
        if self.formatter is None:
            return str(data)
        try:
            return self.formatter.format(data)
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            return str(data)
            
    def set_formatter(self, formatter: BaseFormatter) -> None:
        """フォーマッタを設定"""
        self.formatter = formatter