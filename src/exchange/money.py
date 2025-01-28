# exchange/money.py

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Union, overload
import logging

from .currency import Currency
from .exchange import exchange

class CurrencyConversionError(Exception):
    """通貨変換に関するエラー"""
    pass

@dataclass(frozen=True)
class Money:
    """通貨金額を管理する不変クラス"""
    _logger: logging.Logger = field(default_factory=lambda: logging.getLogger('Money'))
    currency: Currency = field(default=Currency.USD)
    rate_date: date = field(default_factory=date.today)
    _values: Dict[Currency, Decimal] = field(default_factory=dict)

    @overload
    def __init__(
        self, 
        amount: Union[Decimal, float, int], 
        currency: Currency, 
        rate_date: Optional[date] = None
    ):
        """標準的な初期化メソッド"""
        ...

    @overload
    def __init__(
        self, 
        amount: Union[Decimal, float, int], 
        currency: Currency, 
        rate_date: Optional[date] = None,
        *,
        _values: Dict[Currency, Decimal]
    ):
        """内部的な値マップを使用した初期化"""
        ...

    def __init__(
        self, 
        amount: Union[Decimal, float, int], 
        currency: Currency, 
        rate_date: Optional[date] = None,
        *,
        _values: Optional[Dict[Currency, Decimal]] = None
    ):
        """
        Moneyインスタンスの初期化
        
        Args:
            amount: 金額
            currency: 通貨
            rate_date: レート取得日付（デフォルトは今日）
            _values: 内部的な通貨値マップ（主に内部使用）
        """
        object.__setattr__(self, 'currency', currency)
        object.__setattr__(self, 'rate_date', rate_date or date.today())
        
        try:
            converted_amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
            
            if _values is not None:
                object.__setattr__(self, '_values', _values)
                return
            
            values: Dict[Currency, Decimal] = {}
            target_currencies = [Currency.USD, Currency.JPY]
            
            for target_currency in target_currencies:
                if target_currency == currency:
                    values[target_currency] = converted_amount
                else:
                    try:
                        rate = exchange.get_rate(currency, target_currency, self.rate_date)
                        values[target_currency] = rate.convert(converted_amount)
                    except Exception as e:
                        self._logger.warning(f"通貨変換失敗: {currency} -> {target_currency}: {e}")
                        values[target_currency] = Decimal('0')
            
            object.__setattr__(self, '_values', values)
            
        except (TypeError, InvalidOperation) as e:
            raise CurrencyConversionError(f"金額の変換に失敗: {amount}") from e

    def as_currency(self, target_currency: Currency) -> Decimal:
        """指定された通貨の金額を取得"""
        return self._values.get(target_currency, Decimal('0'))

    @property
    def usd(self) -> Decimal:
        """USD金額を返す"""
        return self._values.get(Currency.USD, Decimal('0'))
    
    @property
    def jpy(self) -> Decimal:
        """JPY金額を返す"""
        return self._values.get(Currency.JPY, Decimal('0'))

    def get_rate(self) -> Optional[float]:
        """USD/JPYレートを取得"""
        try:
            rate = self.jpy / self.usd
            return round(float(rate), 2)
        except (ZeroDivisionError, InvalidOperation):
            return None

    def __add__(self, other: 'Money') -> 'Money':
        """加算"""
        new_values = {}
        for currency in self._values.keys():
            new_values[currency] = (
                self._values.get(currency, Decimal('0')) + 
                other._values.get(currency, Decimal('0'))
            )
        return Money(Decimal('0'), self.currency, _values=new_values)

    def __sub__(self, other: 'Money') -> 'Money':
        """減算"""
        new_values = {}
        for currency in self._values.keys():
            new_values[currency] = (
                self._values.get(currency, Decimal('0')) - 
                other._values.get(currency, Decimal('0'))
            )
        return Money(Decimal('0'), self.currency, _values=new_values)

    def __str__(self) -> str:
        """通貨と金額の文字列表現"""
        return f"{self.currency.symbol}{self.as_currency(self.currency):,.2f}"

    def __repr__(self) -> str:
        """開発者向けの詳細な文字列表現"""
        return (f"Money(amount={self.as_currency(self.currency)}, "
                f"currency={self.currency}, "
                f"USD={self.usd}, JPY={self.jpy})")

    @classmethod
    def sum(cls, monies: list['Money']) -> 'Money':
        """Money配列の合計"""
        if not monies:
            return Money(Decimal('0'), Currency.USD)
        
        new_values = {}
        currencies = [Currency.USD, Currency.JPY]
        for currency in currencies:
            new_values[currency] = sum(
                money._values.get(currency, Decimal('0')) 
                for money in monies
            )
        return Money(Decimal('0'), Currency.USD, _values=new_values)