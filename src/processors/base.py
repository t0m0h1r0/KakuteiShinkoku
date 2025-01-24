# base.py
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
        self._tax_records: Dict[str, List[dict]] = {}

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

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """共通の税金トランザクション判定メソッド"""
        tax_actions = {
            'NRA TAX ADJ', 'PR YR NRA TAX', 
            'TAX', 'NRA TAX'
        }
        return transaction.action_type.upper() in tax_actions

    def _process_tax(self, transaction: Transaction, symbol_key: str = 'symbol') -> None:
        """共通の税金トランザクション処理メソッド"""
        symbol = getattr(transaction, symbol_key, 'GENERAL')
        if symbol not in self._tax_records:
            self._tax_records[symbol] = []
        
        self._tax_records[symbol].append({
            'date': transaction.transaction_date,
            'amount': abs(transaction.amount)
        })

    def _find_matching_tax(self, transaction: Transaction, symbol_key: str = 'symbol', max_days: int = 7) -> Decimal:
        """共通の税金マッチングメソッド"""
        symbol = getattr(transaction, symbol_key, 'GENERAL')
        if symbol not in self._tax_records:
            return Decimal('0')

        tax_records = self._tax_records[symbol]
        transaction_date = transaction.transaction_date
       
        for tax_record in tax_records:
            if abs((tax_record['date'] - transaction_date).days) <= max_days:
                return Decimal(tax_record['amount'])

        return Decimal('0')