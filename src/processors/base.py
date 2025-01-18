from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List
from datetime import date
from decimal import Decimal

from ..core.types.transaction import Transaction
from ..core.interfaces import IExchangeRateProvider

T = TypeVar('T')

class BaseProcessor(ABC, Generic[T]):
    """プロセッサーの基底クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        self.exchange_rate_provider = exchange_rate_provider
        self.records: List[T] = []
    
    @abstractmethod
    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理"""
        pass
    
    def process_all(self, transactions: List[Transaction]) -> List[T]:
        """複数トランザクションの一括処理"""
        for transaction in transactions:
            self.process(transaction)
        return self.get_records()
    
    def get_records(self) -> List[T]:
        """処理済みレコードを取得"""
        return sorted(
            self.records, 
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )
    
    def _get_exchange_rate(self, target_date: date) -> Decimal:
        """指定日の為替レートを取得"""
        return self.exchange_rate_provider.get_rate(target_date)
