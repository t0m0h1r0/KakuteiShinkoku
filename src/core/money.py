from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

class Currency:
    """通貨コードの定数"""
    USD = 'USD'
    JPY = 'JPY'
    EUR = 'EUR'
    GBP = 'GBP'
    
    @classmethod
    def is_valid(cls, currency: str) -> bool:
        """通貨コードが有効かを確認"""
        return currency in [cls.USD, cls.JPY, cls.EUR, cls.GBP]

@dataclass(frozen=True)
class Money:
    """金額を表すイミュータブルなデータクラス"""
    amount: Decimal
    currency: str = Currency.USD
    jpy_rate: Optional[Decimal] = None

    def convert_to_jpy(self, exchange_rate: Decimal) -> 'Money':
        """日本円に変換"""
        if self.currency == Currency.JPY:
            return self
        return Money(
            amount=self.amount * exchange_rate,
            currency=Currency.JPY,
            jpy_rate=exchange_rate
        )

    def get_jpy_amount(self) -> Optional[Decimal]:
        """日本円での金額を取得"""
        if self.currency == Currency.JPY:
            return self.amount
        if self.jpy_rate is not None:
            return self.amount * self.jpy_rate
        return None

    def __add__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の加算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(
            self.amount + other.amount,
            self.currency,
            jpy_rate=self.jpy_rate if self.jpy_rate == other.jpy_rate else None
        )

    def __sub__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の減算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
        return Money(
            self.amount - other.amount,
            self.currency,
            jpy_rate=self.jpy_rate if self.jpy_rate == other.jpy_rate else None
        )

    def __mul__(self, multiplier: Decimal) -> 'Money':
        """スカラー乗算"""
        return Money(
            self.amount * multiplier,
            self.currency,
            jpy_rate=self.jpy_rate
        )

    def __truediv__(self, divisor: Decimal) -> 'Money':
        """スカラー除算"""
        return Money(
            self.amount / divisor,
            self.currency,
            jpy_rate=self.jpy_rate
        )

    def __repr__(self) -> str:
        """文字列表現"""
        main_repr = f"{self.currency} {self.amount:,.2f}"
        if self.jpy_rate is not None and self.currency != Currency.JPY:
            jpy_amount = self.get_jpy_amount()
            main_repr += f" (¥{jpy_amount:,.2f})"
        return main_repr