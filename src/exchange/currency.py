# exchange/currency.py

from enum import Enum
from decimal import Decimal
from typing import ClassVar, Dict, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class CurrencyInfo:
    """通貨の詳細情報"""
    code: str
    symbol: str
    decimals: int
    display_name: str

class Currency(Enum):
    """通貨を表現する列挙型"""
    USD = CurrencyInfo('USD', '$', 2, 'US Dollar')
    JPY = CurrencyInfo('JPY', '¥', 0, 'Japanese Yen')
    EUR = CurrencyInfo('EUR', '€', 2, 'Euro')
    GBP = CurrencyInfo('GBP', '£', 2, 'British Pound')

    def __init__(self, info: CurrencyInfo):
        self._info = info

    @property
    def code(self) -> str:
        """通貨コードを取得"""
        return self._info.code

    @property
    def symbol(self) -> str:
        """通貨シンボルを取得"""
        return self._info.symbol

    @property
    def decimals(self) -> int:
        """小数点以下桁数を取得"""
        return self._info.decimals

    @property
    def display_name(self) -> str:
        """表示名を取得"""
        return self._info.display_name

    def format_amount(self, amount: Decimal) -> str:
        """金額のフォーマット"""
        if self.decimals == 0:
            formatted = f"{int(amount):,}"
        else:
            formatted = f"{amount:,.{self.decimals}f}"
        return f"{self.symbol}{formatted}"

    @classmethod
    def from_code(cls, code: str) -> Optional['Currency']:
        """通貨コードから通貨を取得"""
        try:
            upper_code = code.upper()
            return next(
                currency for currency in cls 
                if currency.code == upper_code
            )
        except StopIteration:
            return None

    @classmethod
    def from_symbol(cls, symbol: str) -> Optional['Currency']:
        """通貨シンボルから通貨を取得"""
        try:
            return next(
                currency for currency in cls 
                if currency.symbol == symbol
            )
        except StopIteration:
            return None

    @classmethod
    def from_str(cls, value: str) -> Optional['Currency']:
        """文字列から通貨を取得"""
        if not value:
            return None
            
        # 通貨コードで検索
        currency = cls.from_code(value)
        if currency:
            return currency
            
        # 通貨シンボルで検索
        currency = cls.from_symbol(value)
        if currency:
            return currency
            
        return None

    def __str__(self) -> str:
        return self.code

    def __repr__(self) -> str:
        return f"Currency.{self.name}"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Currency):
            return self.code == other.code
        if isinstance(other, str):
            return self.code == other.upper()
        return False

    def __hash__(self) -> int:
        return hash(self.code)