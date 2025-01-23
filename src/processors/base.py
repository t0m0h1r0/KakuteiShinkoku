from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List
from datetime import date
from decimal import Decimal
import logging

from ..core.transaction import Transaction
from ..exchange.currency import Currency
from ..exchange.money import Money
from ..exchange.rate_provider import RateProvider
from ..exchange.exchange_rate import ExchangeRate

T = TypeVar('T')

class BaseProcessor(ABC, Generic[T]):
    def __init__(self):
        self.records: List[T] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rate_provider = RateProvider()
    
    @abstractmethod
    def process(self, transaction: Transaction) -> None:
        pass
    
    def process_all(self, transactions: List[Transaction]) -> List[T]:
        for transaction in transactions:
            self.process(transaction)
        return self.get_records()
    
    def get_records(self) -> List[T]:
        return sorted(
            self.records, 
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )
    
    def _get_exchange_rate(self, trade_date: date) -> Decimal:
        """為替レートを取得"""
        rate = self._rate_provider.get_rate(
            base_currency=Currency.USD,
            target_currency=Currency.JPY,
            rate_date=trade_date
        )
        return rate.rate
        
    def _create_money(self, amount: Decimal, reference_date: date = None) -> Money:
        if reference_date is None:
            reference_date = date.today()
        return Money(
            amount=amount,
            currency=Currency.USD,
            reference_date=reference_date
        )

    def _create_money_jpy(self, amount: Decimal) -> Money:
        return Money(
            amount=amount,
            currency=Currency.JPY,
            reference_date=date.today()
        )