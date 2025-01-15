from abc import ABC, abstractmethod
from typing import List
from ..models.records import DividendRecord

class ReportWriter(ABC):
    """レポート出力の基底クラス"""
    
    @abstractmethod
    def write(self, records: List[DividendRecord]) -> None:
        """レポートを出力する"""
        pass
