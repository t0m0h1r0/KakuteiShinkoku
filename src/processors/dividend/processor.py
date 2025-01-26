from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money, Currency
from .record import DividendTradeRecord, DividendSummaryRecord
from .tracker import DividendTransactionTracker
from .config import DividendActionTypes, DividendTypes

class DividendProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self._trade_records: List[DividendTradeRecord] = []
        self._summary_records: Dict[str, DividendSummaryRecord] = {}
        self._transaction_tracker = DividendTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_all(self, transactions: List[Transaction]) -> List[DividendTradeRecord]:
        try:
            self.logger.debug("配当トランザクションの処理を開始")
            self._transaction_tracker.track_daily_transactions(transactions)
            
            for symbol, daily_txs in self._transaction_tracker._daily_transactions.items():
                for date in sorted(daily_txs.keys()):
                    self._process_daily_transactions(symbol, daily_txs[date])

            return self.get_records()
        except Exception as e:
            self.logger.error(f"配当処理中にエラーが発生: {e}", exc_info=True)
            return []

    def process(self, transaction: Transaction) -> None:
        try:
            if self._is_tax_transaction(transaction):
                self._process_tax(transaction)
                return

            if not self._is_dividend_transaction(transaction):
                return

            self._process_transaction(transaction)
        except Exception as e:
            self.logger.error(f"取引処理中にエラー: {transaction} - {e}", exc_info=True)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        dividend_transactions = [t for t in transactions if self._is_dividend_transaction(t)]
        for tx in dividend_transactions:
            self._process_transaction(tx)

    def _process_transaction(self, transaction: Transaction) -> None:
        try:
            self.logger.debug(f"配当取引の処理: {transaction.symbol}")
            tax_amount = self._find_matching_tax(transaction)
            
            gross_amount = Money(abs(transaction.amount), Currency.USD)
            tax_money = Money(tax_amount, Currency.USD)

            record = DividendTradeRecord(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                description=transaction.description,
                action_type=transaction.action_type,
                income_type=self._determine_dividend_type(transaction),
                gross_amount=gross_amount,
                tax_amount=tax_money,
                exchange_rate=self._rate_provider.get_rate(
                    Currency.USD, Currency.JPY, transaction.transaction_date)
            )
            
            self._trade_records.append(record)
            self._update_summary_record(record)
            
            self._transaction_tracker.update_tracking(
                transaction.symbol,
                gross_amount.amount,
                tax_money.amount
            )

        except Exception as e:
            self.logger.error(f"配当処理中にエラー: {e}", exc_info=True)
            raise

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        action = transaction.action_type.upper()
        return (
            action in DividendActionTypes.VALID_ACTIONS and 
            abs(transaction.amount) > 0
        )

    def _determine_dividend_type(self, transaction: Transaction) -> str:
        action = transaction.action_type.upper()
        if 'REINVEST' in action:
            return DividendTypes.REINVESTED
        return DividendTypes.CASH

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