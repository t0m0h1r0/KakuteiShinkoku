from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.record import BaseSummaryRecord, BaseTradeRecord

@dataclass
class InterestTradeRecord(BaseTradeRecord):
    action_type: str
    income_type: str
    gross_amount: Money
    tax_amount: Money

@dataclass
class InterestSummaryRecord(BaseSummaryRecord):   
    total_gross_amount: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    total_tax_amount: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
