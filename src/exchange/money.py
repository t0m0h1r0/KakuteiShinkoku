from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union, Dict

from .currency import Currency
from .rate_provider import RateProvider

@dataclass(frozen=True)
class Money:
    """通貨と金額を表すイミュータブルなクラス。
    インスタンス作成時に全通貨の金額を計算し、四則演算時の為替計算を不要にします。
    """
    _amounts: Dict[Currency, Decimal]
    display_currency: Currency

    def __init__(
        self,
        amount: Union[int, float, Decimal],
        currency: Optional[Currency] = None,
        reference_date: Optional[date] = None
    ):
        """初期化メソッド。全通貨での金額を計算します。"""
        display_currency = currency if currency is not None else Currency.USD
        ref_date = reference_date if reference_date is not None else date.today()
        
        # 基準となる金額をDecimalに変換
        base_amount = Decimal(str(amount))
        
        # 全通貨での金額を計算
        rate_provider = RateProvider()
        amounts = {}
        
        for target_currency in Currency.supported_currencies():
            if target_currency == display_currency:
                amounts[target_currency] = base_amount
            else:
                exchange_rate = rate_provider.get_rate(
                    base_currency=display_currency,
                    target_currency=target_currency,
                    rate_date=ref_date
                )
                amounts[target_currency] = exchange_rate.convert(base_amount)

        # イミュータブルなインスタンス変数を設定
        object.__setattr__(self, '_amounts', amounts)
        object.__setattr__(self, 'display_currency', display_currency)

    def __add__(self, other: 'Money') -> 'Money':
        """金額の加算"""
        # 各通貨での合計を計算
        new_amounts = {}
        for currency in Currency.supported_currencies():
            new_amounts[currency] = self._amounts[currency] + other._amounts[currency]
        
        # 新しいMoneyインスタンスを作成
        result = object.__new__(Money)
        object.__setattr__(result, '_amounts', new_amounts)
        object.__setattr__(result, 'display_currency', self.display_currency)
        return result

    def __sub__(self, other: 'Money') -> 'Money':
        """金額の減算"""        
        # 各通貨での差を計算
        new_amounts = {}
        for currency in Currency.supported_currencies():
            new_amounts[currency] = self._amounts[currency] - other._amounts[currency]
        
        # 新しいMoneyインスタンスを作成
        result = object.__new__(Money)
        object.__setattr__(result, '_amounts', new_amounts)
        object.__setattr__(result, 'display_currency', self.display_currency)
        return result

    def __mul__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー乗算"""
        scalar_decimal = Decimal(str(scalar))
        
        # 各通貨での積を計算
        new_amounts = {}
        for currency in Currency.supported_currencies():
            new_amounts[currency] = self._amounts[currency] * scalar_decimal
        
        # 新しいMoneyインスタンスを作成
        result = object.__new__(Money)
        object.__setattr__(result, '_amounts', new_amounts)
        object.__setattr__(result, 'display_currency', self.display_currency)
        return result

    def __truediv__(self, scalar: Union[int, float, Decimal]) -> 'Money':
        """スカラー除算"""
        scalar_decimal = Decimal(str(scalar))
        
        # 各通貨での商を計算
        new_amounts = {}
        for currency in Currency.supported_currencies():
            new_amounts[currency] = self._amounts[currency] / scalar_decimal
        
        # 新しいMoneyインスタンスを作成
        result = object.__new__(Money)
        object.__setattr__(result, '_amounts', new_amounts)
        object.__setattr__(result, 'display_currency', self.display_currency)
        return result

    @property
    def usd(self) -> Decimal:
        """USD金額"""
        return self._amounts[Currency.USD]
    
    @property
    def jpy(self) -> Decimal:
        """JPY金額"""
        return self._amounts[Currency.JPY]
    
    @property
    def eur(self) -> Decimal:
        """EUR金額"""
        return self._amounts[Currency.EUR]
    
    @property
    def gbp(self) -> Decimal:
        """GBP金額"""
        return self._amounts[Currency.GBP]
    
    def as_currency(self, currency: Currency) -> 'Money':
        """表示通貨を変更"""
        result = object.__new__(Money)
        object.__setattr__(result, '_amounts', self._amounts)
        object.__setattr__(result, 'display_currency', currency)
        return result

    def __str__(self) -> str:
        """文字列表現"""
        amount = self._amounts[self.display_currency]
        if self.display_currency == Currency.JPY:
            return f"{self.display_currency} {int(amount):,}"
        return f"{self.display_currency} {amount:.2f}"

    def __repr__(self) -> str:
        """開発者向けの文字列表現"""
        return f"Money(amount={self._amounts[self.display_currency]}, currency={self.display_currency})"