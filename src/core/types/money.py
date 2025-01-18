from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from ..constants.currency import Currency

@dataclass(frozen=True)
class Money:
    """金額を表すイミュータブルなデータクラス"""
    amount: Decimal
    currency: str = Currency.USD

    def convert(self, exchange_rate: Decimal, target_currency: str) -> 'Money':
        """通貨変換メソッド"""
        return Money(
            amount=self.amount * exchange_rate,
            currency=target_currency
        )

    def __add__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の加算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の減算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, multiplier: Decimal) -> 'Money':
        """スカラー乗算"""
        return Money(self.amount * multiplier, self.currency)

    def __truediv__(self, divisor: Decimal) -> 'Money':
        """スカラー除算"""
        return Money(self.amount / divisor, self.currency)

    def __repr__(self) -> str:
        """文字列表現"""
        return f"{self.currency} {self.amount:,.2f}"
