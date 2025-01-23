from dataclasses import dataclass, field
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
    price_jpy: Optional[Money] = None
    realized_gain_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None

    def __post_init__(self):
        if not self.price_jpy:
            self.price_jpy = self.price.as_currency(Currency.JPY)
        if not self.realized_gain_jpy:
            self.realized_gain_jpy = self.realized_gain.as_currency(Currency.JPY)
        if not self.fees_jpy:
            self.fees_jpy = self.fees.as_currency(Currency.JPY)
            
@dataclass  
class StockSummaryRecord:
    account_id: str
    symbol: str
    description: str
    open_date: date
    initial_quantity: Decimal
    close_date: Optional[date] = None
    remaining_quantity: Decimal = Decimal('0')
    total_realized_gain: Money = field(default_factory=lambda: Money(0))
    total_fees: Money = field(default_factory=lambda: Money(0))
    total_realized_gain_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
       
    def __post_init__(self):        
        if not self.total_realized_gain_jpy:
            self.total_realized_gain_jpy = self.total_realized_gain.as_currency(Currency.JPY)
        if not self.total_fees_jpy:
            self.total_fees_jpy = self.total_fees.as_currency(Currency.JPY)