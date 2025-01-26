from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Union, Dict, Optional

from .currency import Currency
from .provider import RateManager
from .types import CurrencyProtocol, MoneyProtocol
from .exchange import exchange

class Money(MoneyProtocol):
    def __init__(
        self, 
        amount: Union[Decimal, float, int], 
        currency: CurrencyProtocol, 
        rate_date: Optional[date] = None,
        _values: Optional[Dict[CurrencyProtocol, Decimal]] = None
    ):
        """
        通貨金額を初期化
        
        Args:
            amount: 金額
            currency: 通貨
            rate_date: 為替レート取得日付（デフォルトは今日）
            _values: 事前計算された通貨変換値（主にコピーコンストラクタ用）
        """
        # 日付のデフォルト値を適切に設定
        if rate_date is None:
            rate_date = date.today()

        # 入力をDecimalに変換
        try:
            amount = Decimal(str(amount))
        except (TypeError, ValueError, InvalidOperation):
            amount = Decimal('0')

        # 事前計算された値が渡された場合
        if _values is not None:
            self._values = _values
            return

        # 為替レート管理
        self._values: Dict[CurrencyProtocol, Decimal] = {}

        # サポートされる通貨で変換
        supported_currencies = [Currency.USD, Currency.JPY]
        for target_currency in supported_currencies:
            if target_currency == currency:
                # 元の通貨はそのまま
                self._values[target_currency] = amount
            else:
                # 他の通貨は為替レートで変換
                try:
                    rate = exchange.get_rate(currency, target_currency, rate_date)
                    try:
                        converted_amount = rate.convert(amount)
                        self._values[target_currency] = converted_amount
                    except (DivisionByZero, InvalidOperation):
                        self._values[target_currency] = Decimal('0')
                except Exception:
                    # 変換に失敗した場合は0を設定
                    self._values[target_currency] = Decimal('0')

    def as_currency(self, target_currency: CurrencyProtocol) -> Decimal:
        """指定通貨の金額を返す"""
        return self._values.get(target_currency, Decimal('0'))
    
    def get_rate(self, base_currency=Currency.USD, target_currency=Currency.JPY):
        try:
            rate = self.jpy / self.usd
            return round(float(rate), 2)
        except Exception:
            return None
  
    @property
    def usd(self) -> Decimal:
        """USD金額を返す"""
        return self._values.get(Currency.USD, Decimal('0'))
    
    @property
    def jpy(self) -> Decimal:
        """JPY金額を返す"""
        return self._values.get(Currency.JPY, Decimal('0'))

    def _safe_divide(self, a: Decimal, b: Decimal) -> Decimal:
        """安全な除算を行う"""
        try:
            return a / b if b != 0 else Decimal('0')
        except (DivisionByZero, InvalidOperation):
            return Decimal('0')

    def __add__(self, other: 'Money') -> 'Money':
        """同じ通貨間の加算"""
        new_values = {}
        for currency in set(list(self._values.keys()) + list(other._values.keys())):
            new_values[currency] = (
                self._values.get(currency, Decimal('0')) + 
                other._values.get(currency, Decimal('0'))
            )
        return Money(Decimal('0'), Currency.USD, _values=new_values)

    def __sub__(self, other: 'Money') -> 'Money':
        """同じ通貨間の減算"""
        new_values = {}
        for currency in set(list(self._values.keys()) + list(other._values.keys())):
            new_values[currency] = (
                self._values.get(currency, Decimal('0')) - 
                other._values.get(currency, Decimal('0'))
            )
        return Money(Decimal('0'), Currency.USD, _values=new_values)

    def __mul__(self, scalar: Union[Decimal, float, int]) -> 'Money':
        """スカラー乗算"""
        try:
            scalar_value = Decimal(str(scalar))
        except (TypeError, ValueError, InvalidOperation):
            scalar_value = Decimal('0')
        
        new_values = {
            currency: value * scalar_value 
            for currency, value in self._values.items()
        }
        return Money(Decimal('0'), Currency.USD, _values=new_values)

    def __truediv__(self, scalar: Union[Decimal, float, int]) -> 'Money':
        """スカラー除算"""
        try:
            scalar_value = Decimal(str(scalar))
            if scalar_value == 0:
                return Money(Decimal('0'), Currency.USD, _values=self._values)
        except (TypeError, ValueError, InvalidOperation):
            return Money(Decimal('0'), Currency.USD, _values=self._values)
        
        new_values = {
            currency: self._safe_divide(value, scalar_value)
            for currency, value in self._values.items()
        }
        return Money(Decimal('0'), Currency.USD, _values=new_values)

    def __str__(self) -> str:
        """文字列表現"""
        return f"USD: {self.usd}, JPY: {self.jpy}"

    @classmethod
    def sum(cls, monies: list['Money']) -> 'Money':
        """Moneyオブジェクトのリストを合計"""
        if not monies:
            return Money(Decimal('0'), Currency.USD)
        
        new_values = {}
        for currency in [Currency.USD, Currency.JPY]:
            new_values[currency] = sum(
                money._values.get(currency, Decimal('0')) 
                for money in monies
            )
        
        return Money(Decimal('0'), Currency.USD, _values=new_values)