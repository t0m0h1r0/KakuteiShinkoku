from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency

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
    
    @property
    def price_jpy(self):
        return self.price.as_currency(Currency.JPY)
    
    @property
    def fees_jpy(self):
        return self.fees.as_currency(Currency.JPY)
    
    @property
    def trading_pnl_jpy(self):
        return self.trading_pnl.as_currency(Currency.JPY)
    
    @property
    def premium_pnl_jpy(self):
        return self.premium_pnl.as_currency(Currency.JPY)

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
    
    @property
    def trading_pnl_jpy(self):
        return self.trading_pnl.as_currency(Currency.JPY)
    
    @property
    def premium_pnl_jpy(self):
        return self.premium_pnl.as_currency(Currency.JPY)
    
    @property
    def total_fees_jpy(self):
        return self.total_fees.as_currency(Currency.JPY)