from dataclasses import dataclass
from datetime import date
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Dict, Optional

from .currency import Currency
from .exchange import exchange

class Money:
   """通貨金額を管理するクラス"""
   def __init__(
       self, 
       amount: Decimal, 
       currency: Currency, 
       rate_date: Optional[date] = None,
       _values: Optional[Dict[Currency, Decimal]] = None
   ):
       if rate_date is None:
           rate_date = date.today()

       try:
           amount = Decimal(str(amount))
       except (TypeError, ValueError, InvalidOperation):
           amount = Decimal('0')

       if _values is not None:
           self._values = _values
           return

       self._values: Dict[Currency, Decimal] = {}
       
       # USD/JPYの変換のみをサポート
       target_currencies = [Currency.USD, Currency.JPY]
       for target_currency in target_currencies:
           if target_currency == currency:
               self._values[target_currency] = amount
           else:
               try:
                   rate = exchange.get_rate(currency, target_currency, rate_date)
                   converted_amount = rate.convert(amount)
                   self._values[target_currency] = converted_amount
               except Exception:
                   self._values[target_currency] = Decimal('0')

   def as_currency(self, target_currency: Currency) -> Decimal:
       """指定通貨の金額を返す"""
       return self._values.get(target_currency, Decimal('0'))
   
   def get_rate(self) -> Optional[float]:
       """USD/JPYレートを取得"""
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

   def __add__(self, other: 'Money') -> 'Money':
       """加算"""
       new_values = {}
       for currency in self._values.keys():
           new_values[currency] = (
               self._values.get(currency, Decimal('0')) + 
               other._values.get(currency, Decimal('0'))
           )
       return Money(Decimal('0'), Currency.USD, _values=new_values)

   def __sub__(self, other: 'Money') -> 'Money':
       """減算"""
       new_values = {}
       for currency in self._values.keys():
           new_values[currency] = (
               self._values.get(currency, Decimal('0')) - 
               other._values.get(currency, Decimal('0'))
           )
       return Money(Decimal('0'), Currency.USD, _values=new_values)

   def __str__(self) -> str:
       return f"USD: {self.usd}, JPY: {self.jpy}"

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