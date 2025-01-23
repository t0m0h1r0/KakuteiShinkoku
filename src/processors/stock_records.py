from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money, Currency

@dataclass
class StockTradeRecord:
    trade_date: date
    account_id: str 
    symbol: str
    description: str
    action: str
    quantity: Decimal
    price: Money
    realized_gain: Money
    fees: Money
    exchange_rate: Decimal
    
    @property
    def price_jpy(self):
        return self.price.as_currency(Currency.JPY)
    
    @property
    def realized_gain_jpy(self):
        return self.realized_gain.as_currency(Currency.JPY)
    
    @property
    def fees_jpy(self):
        return self.fees.as_currency(Currency.JPY)

@dataclass  
class StockSummaryRecord:
    account_id: str
    symbol: str
    description: str
    open_date: date
    initial_quantity: Decimal
    close_date: Optional[date] = None
    remaining_quantity: Decimal = Decimal('0')
    total_realized_gain: Money = Money(0)
    total_fees: Money = Money(0)