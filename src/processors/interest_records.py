from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency

@dataclass
class InterestTradeRecord:
    """利子取引記録"""
    record_date: date
    account_id: str
    symbol: str
    description: str
    income_type: str
    action_type: str
    is_matured: bool
    
    gross_amount: Money
    tax_amount: Money
    
    exchange_rate: Decimal
    
    @property
    def gross_amount_jpy(self):
        return self.gross_amount.as_currency(Currency.JPY)
    
    @property
    def tax_amount_jpy(self):
        return self.tax_amount.as_currency(Currency.JPY)

@dataclass
class InterestSummaryRecord:
    """利子サマリー記録"""
    account_id: str
    symbol: str
    description: str
    
    total_gross_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_tax_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    
    @property
    def total_gross_amount_jpy(self):
        return self.total_gross_amount.as_currency(Currency.JPY)
    
    @property
    def total_tax_amount_jpy(self):
        return self.total_tax_amount.as_currency(Currency.JPY)