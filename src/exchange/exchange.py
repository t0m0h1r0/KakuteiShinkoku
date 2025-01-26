from datetime import date
from decimal import Decimal
from typing import Protocol, runtime_checkable

from .currency import Currency
from .money import Money
from .provider import RateManager
from .rate import Rate

class ExchangeService:
    """為替変換と通貨関連のサービスを提供するクラス"""
    def __init__(self):
        self._rate_manager = RateManager()

    def convert(self, amount: Decimal, from_currency: Currency, to_currency: Currency, conversion_date: date = None) -> Money:
        """通貨を変換"""
        if conversion_date is None:
            conversion_date = date.today()
        
        rate = self._rate_manager.get_rate(from_currency, to_currency, conversion_date)
        converted_amount = rate.convert(amount)
        
        return Money(converted_amount, to_currency, conversion_date)

    def get_rate(self, base: Currency, target: Currency, rate_date: date = None) -> Rate:
        """特定の日付の為替レートを取得"""
        if rate_date is None:
            rate_date = date.today()
        
        return self._rate_manager.get_rate(base, target, rate_date)

    def add_rate_source(self, base: Currency, target: Currency, default_rate: Decimal, history_file=None):
        """レートソースを追加"""
        from .provider import RateSource
        source = RateSource(base, target, default_rate, history_file)
        self._rate_manager.add_source(source)

@runtime_checkable
class ExchangeServiceProtocol(Protocol):
    """為替サービスのプロトコル定義"""
    def convert(self, amount: Decimal, from_currency: Currency, to_currency: Currency, conversion_date: date = None) -> Money: ...
    def get_rate(self, base: Currency, target: Currency, rate_date: date = None) -> Rate: ...
    def add_rate_source(self, base: Currency, target: Currency, default_rate: Decimal, history_file=None): ...

# グローバルインスタンス
exchange = ExchangeService()