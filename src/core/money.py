from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
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

    def __post_init__(self):
        """初期化後の処理"""
        # 日本円の場合は整数に丸める
        if self.currency == Currency.JPY:
            object.__setattr__(self, 'amount', 
                self.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

    def convert_to_jpy(self, exchange_rate: Decimal) -> 'Money':
        """日本円に変換"""
        if self.currency == Currency.JPY:
            return self
            
        # 日本円に変換時は整数に丸める
        jpy_amount = (self.amount * exchange_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Money(
            amount=jpy_amount,
            currency=Currency.JPY,
            jpy_rate=exchange_rate
        )

    def get_jpy_amount(self) -> Optional[Decimal]:
        """日本円での金額を取得"""
        if self.currency == Currency.JPY:
            return self.amount
        if self.jpy_rate is not None:
            return (self.amount * self.jpy_rate).quantize(
                Decimal('1'), rounding=ROUND_HALF_UP)
        return None

    def __add__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の加算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        
        new_amount = self.amount + other.amount
        # 日本円の場合は整数に丸める
        if self.currency == Currency.JPY:
            new_amount = new_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Money(
            new_amount,
            self.currency,
            jpy_rate=self.jpy_rate if self.jpy_rate == other.jpy_rate else None
        )

    def __sub__(self, other: 'Money') -> 'Money':
        """通貨が同じ場合の減算"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract {other.currency} from {self.currency}")
            
        new_amount = self.amount - other.amount
        # 日本円の場合は整数に丸める
        if self.currency == Currency.JPY:
            new_amount = new_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Money(
            new_amount,
            self.currency,
            jpy_rate=self.jpy_rate if self.jpy_rate == other.jpy_rate else None
        )

    def __mul__(self, multiplier: Decimal) -> 'Money':
        """スカラー乗算"""
        new_amount = self.amount * multiplier
        # 日本円の場合は整数に丸める
        if self.currency == Currency.JPY:
            new_amount = new_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Money(
            new_amount,
            self.currency,
            jpy_rate=self.jpy_rate
        )

    def __truediv__(self, divisor: Decimal) -> 'Money':
        """スカラー除算"""
        new_amount = self.amount / divisor
        # 日本円の場合は整数に丸める
        if self.currency == Currency.JPY:
            new_amount = new_amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            
        return Money(
            new_amount,
            self.currency,
            jpy_rate=self.jpy_rate
        )

    def __repr__(self) -> str:
        """文字列表現"""
        main_repr = f"{self.currency} {self.amount:,.2f}"
        if self.jpy_rate is not None and self.currency != Currency.JPY:
            jpy_amount = self.get_jpy_amount()
            if jpy_amount is not None:
                main_repr += f" (¥{jpy_amount:,})"
        return main_repr