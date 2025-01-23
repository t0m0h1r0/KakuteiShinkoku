from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class OptionTradeRecord:
    """オプション取引記録"""
    trade_date: date
    account_id: str
    symbol: str
    description: str
    action: str
    quantity: Decimal
    price: Money
    fees: Money
    exchange_rate: Decimal
    option_type: str     
    strike_price: Decimal
    expiry_date: date
    underlying: str
    trading_pnl: Money   
    premium_pnl: Money   
    position_type: str   
    is_closed: bool      
    is_expired: bool     
    is_assigned: bool    
    price_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    trading_pnl_jpy: Optional[Money] = None
    premium_pnl_jpy: Optional[Money] = None
    
    def __post_init__(self):
        if isinstance(self.quantity, int):
            object.__setattr__(self, 'quantity', Decimal(str(self.quantity)))
            
        if isinstance(self.strike_price, (int, float)):
            object.__setattr__(self, 'strike_price', Decimal(str(self.strike_price)))
        
        if not self.price_jpy:
            object.__setattr__(self, 'price_jpy', self.price.as_currency(Currency.JPY))
        
        if not self.fees_jpy:
            object.__setattr__(self, 'fees_jpy', self.fees.as_currency(Currency.JPY))
        
        if not self.trading_pnl_jpy:
            object.__setattr__(self, 'trading_pnl_jpy', self.trading_pnl.as_currency(Currency.JPY))
        
        if not self.premium_pnl_jpy:
            object.__setattr__(self, 'premium_pnl_jpy', self.premium_pnl.as_currency(Currency.JPY))

@dataclass
class OptionSummaryRecord:
    """オプション取引サマリー記録"""
    account_id: str
    symbol: str
    description: str
    underlying: str
    option_type: str
    strike_price: Decimal
    expiry_date: date
    open_date: date
    close_date: Optional[date] = None
    status: str = 'Open'
    initial_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    trading_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    premium_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0')))
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    trading_pnl_jpy: Optional[Money] = None
    premium_pnl_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        if isinstance(self.initial_quantity, int):
            object.__setattr__(self, 'initial_quantity', Decimal(str(self.initial_quantity)))
        if isinstance(self.remaining_quantity, int):
            object.__setattr__(self, 'remaining_quantity', Decimal(str(self.remaining_quantity)))
        if isinstance(self.strike_price, (int, float)):
            object.__setattr__(self, 'strike_price', Decimal(str(self.strike_price)))
        
        if not self.trading_pnl_jpy:
            object.__setattr__(self, 'trading_pnl_jpy', self.trading_pnl.as_currency(Currency.JPY))
        
        if not self.premium_pnl_jpy:
            object.__setattr__(self, 'premium_pnl_jpy', self.premium_pnl.as_currency(Currency.JPY))
        
        if not self.total_fees_jpy:
            object.__setattr__(self, 'total_fees_jpy', self.total_fees.as_currency(Currency.JPY))