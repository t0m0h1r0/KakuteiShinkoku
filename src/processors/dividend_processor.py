from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency, RateProvider
from .base import BaseProcessor
from .dividend_records import DividendTradeRecord, DividendSummaryRecord

class DividendProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self._trade_records: List[DividendTradeRecord] = []
        self._summary_records: Dict[str, DividendSummaryRecord] = {}

    def process(self, transaction: Transaction) -> None:
        if self._is_tax_transaction(transaction):
            self._process_tax(transaction)
            return

        if not self._is_dividend_transaction(transaction):
            return

        tax_amount = self._find_matching_tax(transaction)
        
        gross_amount = self._create_money(abs(transaction.amount))
        tax_money = self._create_money(tax_amount)

        dividend_record = DividendTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type='Dividend',
            action_type=transaction.action_type,
            gross_amount=gross_amount,
            tax_amount=tax_money,
            exchange_rate=RateProvider().get_rate(Currency.USD,Currency.JPY,transaction.transaction_date).rate,
        )
        self._trade_records.append(dividend_record)
        self._update_summary_record(dividend_record)

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        dividend_actions = {
            'DIVIDEND', 
            'CASH DIVIDEND',
            'REINVEST DIVIDEND',
            'PR YR CASH DIV'
        }
        return (transaction.action_type.upper() in dividend_actions and 
                abs(transaction.amount) > Decimal('0'))

    def _update_summary_record(self, dividend_record: DividendTradeRecord) -> None:
        symbol = dividend_record.symbol or 'GENERAL'
        
        if symbol not in self._summary_records:
            self._summary_records[symbol] = DividendSummaryRecord(
                account_id=dividend_record.account_id,
                symbol=symbol,
                description=dividend_record.description,
            )
        
        summary = self._summary_records[symbol]
        summary.total_gross_amount += dividend_record.gross_amount
        summary.total_tax_amount += dividend_record.tax_amount

    def get_records(self) -> List[DividendTradeRecord]:
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[DividendSummaryRecord]:
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)