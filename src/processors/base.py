from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List
from datetime import date
from decimal import Decimal
import logging

from ..core.transaction import Transaction
from ..core.interfaces import IExchangeRateProvider
from ..exchange.currency import Currency
from ..exchange.money import Money

T = TypeVar('T')

class BaseProcessor(ABC, Generic[T]):
    """プロセッサーの基底クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        self.exchange_rate_provider = exchange_rate_provider
        self.records: List[T] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
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
        rate = self.exchange_rate_provider.get_rate(
            base_currency=Currency.USD, 
            target_currency=Currency.JPY, 
            rate_date=target_date
        )
        return rate.rate
    
    def _convert_money_to_jpy(self, usd_money: Money) -> Money:
        """USD金額を日本円に変換"""
        return usd_money.convert(Currency.JPY)

    def _create_money_with_rate(self, amount: Decimal, exchange_rate: Decimal) -> Money:
        """為替レート付きでMoneyオブジェクトを作成"""
        return Money(
            amount=amount, 
            currency=Currency.USD, 
            reference_date=date.today()
        )