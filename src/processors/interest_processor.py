from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .interest_records import InterestTradeRecord, InterestSummaryRecord

class InterestProcessor(BaseProcessor):
   def __init__(self, exchange_rate_provider: IExchangeRateProvider):
       super().__init__(exchange_rate_provider)
       self._tax_records: Dict[str, List[dict]] = {}
       self._trade_records: List[InterestTradeRecord] = []
       self._summary_records: Dict[str, InterestSummaryRecord] = {}

   def process(self, transaction: Transaction) -> None:
       if not self._is_interest_transaction(transaction):
           return

       if self._is_tax_transaction(transaction):
           self._process_tax(transaction)
           return

       exchange_rate = self._get_exchange_rate(transaction.transaction_date)
       tax_amount = self._find_matching_tax(transaction)
       
       gross_amount = self._create_money(abs(transaction.amount))
       tax_money = self._create_money(tax_amount)

       interest_record = InterestTradeRecord(
           record_date=transaction.transaction_date,
           account_id=transaction.account_id,
           symbol=transaction.symbol or '',
           description=transaction.description,
           income_type=self._determine_income_type(transaction),
           action_type=transaction.action_type,
           is_matured='MATURED' in transaction.description.upper(),
           gross_amount=gross_amount,
           tax_amount=tax_money,
           exchange_rate=exchange_rate
       )
       
       self._trade_records.append(interest_record)
       self._update_summary_record(interest_record)

   def _is_interest_transaction(self, transaction: Transaction) -> bool:
       interest_actions = {
           'CREDIT INTEREST',
           'BANK INTEREST',
           'BOND INTEREST',
           'CD INTEREST',
           'PR YR BANK INT',
       }
       return (transaction.action_type.upper() in interest_actions and 
               abs(transaction.amount) > Decimal('0'))

   def _is_tax_transaction(self, transaction: Transaction) -> bool:
       return 'TAX' in transaction.action_type.upper()

   def _process_tax(self, transaction: Transaction) -> None:
       symbol = transaction.symbol or 'GENERAL'
       if symbol not in self._tax_records:
           self._tax_records[symbol] = []
       
       self._tax_records[symbol].append({
           'date': transaction.transaction_date,
           'amount': abs(transaction.amount)
       })

   def _find_matching_tax(self, transaction: Transaction) -> Decimal:
       symbol = transaction.symbol or 'GENERAL'
       if symbol not in self._tax_records:
           return Decimal('0')

       tax_records = self._tax_records[symbol]
       transaction_date = transaction.transaction_date
       
       for tax_record in tax_records:
           if abs((tax_record['date'] - transaction_date).days) <= 7:
               return Decimal(tax_record['amount'])

       return Decimal('0')

   def _determine_income_type(self, transaction: Transaction) -> str:
       action = transaction.action_type.upper()
       
       if action == 'CD INTEREST':
           return 'CD Interest'
       elif action == 'BOND INTEREST':
           return 'Bond Interest'
       elif action == 'BANK INTEREST':
           return 'Bank Interest'
       elif action == 'CREDIT INTEREST':
           return 'Credit Interest'
       return 'Other Interest'

   def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
       symbol = interest_record.symbol or 'GENERAL'
       
       if symbol not in self._summary_records:
           self._summary_records[symbol] = InterestSummaryRecord(
               account_id=interest_record.account_id,
               symbol=symbol,
               description=interest_record.description,
               exchange_rate=interest_record.exchange_rate
           )
       
       summary = self._summary_records[symbol]
       summary.total_gross_amount += interest_record.gross_amount
       summary.total_tax_amount += interest_record.tax_amount

   def get_records(self) -> List[InterestTradeRecord]:
       return sorted(self._trade_records, key=lambda x: x.record_date)

   def get_summary_records(self) -> List[InterestSummaryRecord]:
       return sorted(self._summary_records.values(), key=lambda x: x.symbol)