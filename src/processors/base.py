from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Dict
from datetime import date
from decimal import Decimal
import logging

from src.core.interfaces import IProcessor, IExchangeRateProvider
from src.core.models import Transaction, Money
from src.config.constants import Currency

T = TypeVar('T')  # Record type (DividendRecord, TradeRecord, etc.)

class BaseProcessor(IProcessor, Generic[T]):
    """処理の基底クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        self.exchange_rate_provider = exchange_rate_provider
        self.records: List[T] = []
        self._logger = logging.getLogger(self.__class__.__name__)

    def process(self, transaction: Transaction) -> None:
        """
        単一トランザクションの処理
        """
        try:
            if self._is_target_transaction(transaction):
                self._process_transaction(transaction)
        except Exception as e:
            self._logger.error(f"Transaction processing error: {e}", exc_info=True)
            raise

    def process_all(self, transactions: List[Transaction]) -> List[T]:
        """
        複数トランザクションの一括処理
        """
        for transaction in transactions:
            try:
                self.process(transaction)
            except Exception as e:
                self._logger.error(f"Error processing transaction: {e}")
                continue
        return self.get_records()

    def get_records(self) -> List[T]:
        """処理済みレコードを取得"""
        return sorted(
            self.records, 
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )

    @abstractmethod
    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """処理対象のトランザクションかどうかを判定"""
        pass

    @abstractmethod
    def _process_transaction(self, transaction: Transaction) -> None:
        """個別のトランザクション処理を実装"""
        pass

    def _get_exchange_rate(self, date_: date) -> Decimal:
        """為替レートを取得"""
        return self.exchange_rate_provider.get_rate(date_)

    def _create_money(self, amount: Decimal, currency: str = Currency.USD) -> Money:
        """Money オブジェクトを作成"""
        return Money(amount=amount, currency=currency)