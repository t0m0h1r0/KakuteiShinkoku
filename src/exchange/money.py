from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

from .currency import Currency
from .exchange_rate import ExchangeRate
from .rate_provider import RateProvider

@dataclass(frozen=True)
class Money:
    """通貨と金額を表すイミュータブルなクラス"""
    amount: Decimal
    currency: Currency = Currency.USD
    reference_date: Optional[date] = None
    
    def __post_init__(self):
        """入力値の検証と型変換"""
        # Decimalへの変換
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        
        # 参照日付のデフォルト値
        if self.reference_date is None:
            object.__setattr__(self, 'reference_date', date.today())

    def __add__(self, other: 'Money') -> 'Money':
        """同じ通貨の加算"""
        self._validate_currency_operation(other)
        return Money(
            self.amount + other.amount, 
            self.currency, 
            max(self.reference_date, other.reference_date)
        )

    def __sub__(self, other: 'Money') -> 'Money':
        """同じ通貨の減算"""
        self._validate_currency_operation(other)
        return Money(
            self.amount - other.amount, 
            self.currency, 
            max(self.reference_date, other.reference_date)
        )

    def __mul__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー乗算"""
        scalar_decimal = Decimal(str(scalar))
        return Money(
            self.amount * scalar_decimal, 
            self.currency, 
            self.reference_date
        )

    def __truediv__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー除算"""
        scalar_decimal = Decimal(str(scalar))
        return Money(
            self.amount / scalar_decimal, 
            self.currency, 
            self.reference_date
        )

    def _validate_currency_operation(self, other: 'Money'):
        """通貨の同一性を検証"""
        if self.currency != other.currency:
            raise ValueError(f"異なる通貨間の演算: {self.currency} vs {other.currency}")

    def convert(self, target_currency: Currency, rate_provider: Optional[RateProvider] = None) -> 'Money':
        """指定された通貨に変換"""
        # 通貨が同じ場合は何もしない
        if self.currency == target_currency:
            return self

        # RateProviderがない場合はデフォルトを使用
        if rate_provider is None:
            rate_provider = RateProvider()

        # 為替レートを取得
        exchange_rate = rate_provider.get_rate(
            base_currency=self.currency, 
            target_currency=target_currency, 
            date=self.reference_date
        )

        # 変換
        converted_amount = exchange_rate.convert(self.amount)

        return Money(
            amount=converted_amount, 
            currency=target_currency, 
            reference_date=self.reference_date
        )

    def __str__(self) -> str:
        """文字列表現"""
        # 通貨に応じて異なる小数点表示
        if self.currency == Currency.JPY:
            return f"{self.currency} {int(self.amount):,}"
        return f"{self.currency} {self.amount:.2f}"

    def __repr__(self) -> str:
        """開発者向けの文字列表現"""
        return f"Money(amount={self.amount}, currency={self.currency}, date={self.reference_date})"