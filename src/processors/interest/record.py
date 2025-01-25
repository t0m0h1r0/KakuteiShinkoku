from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.record import BaseSummaryRecord, BaseTradeRecord

@dataclass
class InterestTradeRecord(BaseTradeRecord):
    """利子取引記録"""
    action_type: str
    income_type: str
    #is_matured: bool
    
    gross_amount: Money
    tax_amount: Money
    
    @property
    def gross_amount_jpy(self):
        return self.gross_amount.as_currency(Currency.JPY)
    
    @property
    def tax_amount_jpy(self):
        return self.tax_amount.as_currency(Currency.JPY)

@dataclass
class InterestSummaryRecord(BaseSummaryRecord):   
    total_gross_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_tax_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    
    @property
    def total_gross_amount_jpy(self):
        return self.total_gross_amount.as_currency(Currency.JPY)
    
    @property
    def total_tax_amount_jpy(self):
        return self.total_tax_amount.as_currency(Currency.JPY)