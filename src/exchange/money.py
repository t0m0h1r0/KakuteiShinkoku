from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Union, List, Optional

from .currency import Currency
from .provider import RateManager
from .types import CurrencyProtocol, MoneyProtocol

@dataclass(frozen=True)
class Money(MoneyProtocol):
    """通貨と金額を表現するイミュータブルなクラス"""
    amount: Decimal
    currency: CurrencyProtocol
    rate_date: date = field(default_factory=date.today)
    
    def __post_init__(self):
        """パラメータの初期化と検証"""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))

    def convert(self, target_currency: CurrencyProtocol) -> 'Money':
        """指定された通貨に変換"""
        rate_manager = RateManager()
        rate = rate_manager.get_rate(self.currency, target_currency, self.rate_date)
        converted_amount = rate.convert(self.amount)
        return Money(converted_amount, target_currency, self.rate_date)

    def as_currency(self, target_currency: CurrencyProtocol) -> 'Money':
        """指定通貨で表現"""
        if self.currency == target_currency:
            return self
        return self.convert(target_currency)
  
    @property
    def usd(self) -> Decimal:
        """USD表示"""
        if self.currency == Currency.USD:
            return self.amount
        return self.convert(Currency.USD).amount
    
    @property
    def jpy(self) -> Decimal:
        """JPY表示"""
        if self.currency == Currency.JPY:
            return self.amount
        return self.convert(Currency.JPY).amount

    def __add__(self, other: 'Money') -> 'Money':
        """同じ通貨の場合のみ加算"""
        if self.currency.code != other.currency.code:
            raise ValueError("異なる通貨間の加算はできません")
        return Money(self.amount + other.amount, self.currency, self.rate_date)

    def __radd__(self, other: 'Money') -> 'Money':
        return self.__add__(other)

    def __sub__(self, other: 'Money') -> 'Money':
        """同じ通貨の場合のみ減算"""
        if self.currency.code != other.currency.code:
            raise ValueError("異なる通貨間の減算はできません")
        return Money(self.amount - other.amount, self.currency, self.rate_date)

    def __mul__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー乗算"""
        scalar_value = Decimal(str(scalar))
        return Money(self.amount * scalar_value, self.currency, self.rate_date)

    def __truediv__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー除算"""
        scalar_value = Decimal(str(scalar))
        return Money(self.amount / scalar_value, self.currency, self.rate_date)

    def __str__(self) -> str:
        """文字列表現"""
        return f"{self.currency.symbol}{self.format()}"

    def format(self, decimal_places: Optional[int] = None) -> str:
        """金額のフォーマット"""
        if decimal_places is None:
            decimal_places = self.currency.decimals

        if self.currency.code == Currency.JPY.code:
            return f"{int(self.amount):,}"
        
        return f"{self.amount:.{decimal_places}f}"

    @staticmethod
    def sum(monies: List['Money']) -> 'Money':
        """同じ通貨のMoneyオブジェクトの合計を計算"""
        if not monies:
            raise ValueError("空のリストは許可されません")
        
        currency = monies[0].currency
        if not all(m.currency.code == currency.code for m in monies):
            raise ValueError("異なる通貨のMoneyオブジェクトは合計できません")
        
        total_amount = sum(m.amount for m in monies)
        return Money(total_amount, currency, monies[0].rate_date)