from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.record import BaseSummaryRecord, BaseTradeRecord

@dataclass
class StockTradeRecord(BaseTradeRecord):
    action: str
    quantity: Decimal
    price: Money
    realized_gain: Money
    fees: Money
    
    @property
    def price_jpy(self) -> Money:
        return self.price.as_currency(Currency.JPY)
    
    @property
    def realized_gain_jpy(self) -> Money:
        return self.realized_gain.as_currency(Currency.JPY)
    
    @property
    def fees_jpy(self) -> Money:
        return self.fees.as_currency(Currency.JPY)

@dataclass
class StockSummaryRecord(BaseSummaryRecord):
    initial_quantity: Decimal = Decimal('0')
    total_realized_gain: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    
    @property
    def total_realized_gain_jpy(self) -> Money:
        return self.total_realized_gain.as_currency(Currency.JPY)
    
    @property
    def total_fees_jpy(self) -> Money:
        return self.total_fees.as_currency(Currency.JPY)
    
    @property
    def net_profit(self) -> Money:
        return self.total_realized_gain - self.total_fees
    
    @property
    def net_profit_jpy(self) -> Money:
        return self.net_profit.as_currency(Currency.JPY)