from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date

from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.record import BaseSummaryRecord, BaseTradeRecord

@dataclass
class DividendTradeRecord(BaseTradeRecord):
   action_type: str
   income_type: str
   gross_amount: Money
   tax_amount: Money
   
   @property
   def gross_amount_jpy(self):
       return self.gross_amount.as_currency(Currency.JPY)
   
   @property
   def tax_amount_jpy(self):
       return self.tax_amount.as_currency(Currency.JPY)

@dataclass
class DividendSummaryRecord(BaseSummaryRecord):   
   total_gross_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
   total_tax_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
   
   @property
   def total_gross_amount_jpy(self):
       return self.total_gross_amount.as_currency(Currency.JPY)
   
   @property
   def total_tax_amount_jpy(self):
       return self.total_tax_amount.as_currency(Currency.JPY)