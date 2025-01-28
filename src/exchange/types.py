# exchange/types.py
from typing import Protocol, runtime_checkable, Optional
from datetime import date
from decimal import Decimal

@runtime_checkable
class CurrencyProtocol(Protocol):
    """通貨に関するプロトコル"""
    @property
    def code(self) -> str: ...
    @property
    def symbol(self) -> str: ...
    @property
    def decimals(self) -> int: ...

@runtime_checkable
class RateProtocol(Protocol):
    """為替レートのプロトコル"""
    base: CurrencyProtocol
    target: CurrencyProtocol
    value: Decimal
    date: date

    def convert(self, amount: Decimal) -> Decimal: ...
    def inverse(self) -> 'RateProtocol': ...

@runtime_checkable
class MoneyProtocol(Protocol):
    """金額のプロトコル"""
    amount: Decimal | float | int
    currency: CurrencyProtocol
    rate_date: date

    def convert(self, target_currency: CurrencyProtocol) -> 'MoneyProtocol': ...
    def format(self, decimal_places: Optional[int] = None) -> str: ...