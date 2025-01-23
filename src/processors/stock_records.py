from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class StockTradeRecord:
    """株式取引記録"""
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
        if isinstance(self.quantity, int):
            object.__setattr__(self, 'quantity', Decimal(str(self.quantity)))
        
        if not self.price_jpy:
            object.__setattr__(self, 'price_jpy', self.price.as_currency(Currency.JPY))
        
        if not self.realized_gain_jpy:
            object.__setattr__(self, 'realized_gain_jpy', self.realized_gain.as_currency(Currency.JPY))
        
        if not self.fees_jpy:
            object.__setattr__(self, 'fees_jpy', self.fees.as_currency(Currency.JPY))

@dataclass
class StockSummaryRecord:
    """株式取引サマリー記録"""
    account_id: str
    symbol: str
    description: str
    open_date: date
    close_date: Optional[date] = None
    status: str = 'Open'
    initial_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    total_realized_gain: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0')))
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    total_realized_gain_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        if isinstance(self.initial_quantity, int):
            object.__setattr__(self, 'initial_quantity', Decimal(str(self.initial_quantity)))
        
        if isinstance(self.remaining_quantity, int):
            object.__setattr__(self, 'remaining_quantity', Decimal(str(self.remaining_quantity)))
        
        if not self.total_realized_gain_jpy:
            object.__setattr__(self, 'total_realized_gain_jpy', self.total_realized_gain.as_currency(Currency.JPY))
        
        if not self.total_fees_jpy:
            object.__setattr__(self, 'total_fees_jpy', self.total_fees.as_currency(Currency.JPY))