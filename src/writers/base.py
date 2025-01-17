from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Protocol
from datetime import date
import logging

from ..config.settings import FILE_ENCODING
from ..core.models import Money

class Record(Protocol):
    """レコードプロトコル"""
    record_date: date

class BaseWriter(ABC):
    """出力処理の基底クラス"""
    
    def __init__(self, encoding: str = FILE_ENCODING):
        self.encoding = encoding
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def write(self, records: List[Record]) -> None:
        """レコードを出力"""
        pass

    def _format_money(self, money: Money, precision: int = 2) -> str:
        """金額のフォーマット"""
        return f"{round(money.amount, precision):,.{precision}f}"

    def _format_percentage(self, value: Decimal, precision: int = 2) -> str:
        """パーセント値のフォーマット"""
        return f"{round(value, precision):,.{precision}f}%"

    def _ensure_output_dir(self, path: Path) -> None:
        """出力ディレクトリの存在確認"""
        path.parent.mkdir(parents=True, exist_ok=True)

class WriterError(Exception):
    """Writer関連のエラー"""
    pass
