from typing import List, Dict
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency

from .record import DividendTradeRecord, DividendSummaryRecord
from .tracker import DividendTransactionTracker
from .config import DividendActionTypes, DividendTypes


class DividendProcessor(BaseProcessor[DividendTradeRecord]):
    def __init__(self):
        super().__init__()
        self._summary_records: Dict[str, DividendSummaryRecord] = {}
        self._transaction_tracker = DividendTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(
        self, symbol: str, transactions: List[Transaction]
    ) -> None:
        """日次トランザクションを処理"""
        # 税金トランザクションの処理
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        # 配当トランザクションの処理
        dividend_transactions = [
            t for t in transactions if self._is_dividend_transaction(t)
        ]
        for transaction in dividend_transactions:
            self._process_transaction(transaction)

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションを処理"""
        try:
            if self._is_tax_transaction(transaction):
                self._process_tax(transaction)
                return

            if not self._is_dividend_transaction(transaction):
                return

            self._process_transaction(transaction)
        except Exception as e:
            self.logger.error(f"取引処理中にエラー: {transaction} - {e}")

    def _process_transaction(self, transaction: Transaction) -> None:
        """配当トランザクションの処理"""
        try:
            tax_amount = self._find_matching_tax(transaction)

            # Money クラスを使用
            gross_amount = Money(
                abs(transaction.amount), Currency.USD, transaction.transaction_date
            )
            tax_money = Money(tax_amount, Currency.USD, transaction.transaction_date)

            record = DividendTradeRecord(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                description=transaction.description,
                action_type=transaction.action_type,
                income_type=self._determine_dividend_type(transaction),
                gross_amount=gross_amount,
                tax_amount=tax_money,
                exchange_rate=gross_amount.get_rate(),
            )

            self._trade_records.append(record)
            self._update_summary_record(record)

            self._transaction_tracker.update_tracking(
                transaction.symbol, gross_amount.usd, tax_money.usd
            )

        except Exception as e:
            self.logger.error(f"配当処理中にエラー: {e}")
            raise

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当トランザクションの判定"""
        action = transaction.action_type.upper()
        return (
            action in DividendActionTypes.VALID_ACTIONS and abs(transaction.amount) > 0
        )

    def _determine_dividend_type(self, transaction: Transaction) -> str:
        """配当の種類を決定"""
        action = transaction.action_type.upper()
        if "REINVEST" in action:
            return DividendTypes.REINVESTED
        return DividendTypes.CASH

    def _update_summary_record(self, dividend_record: DividendTradeRecord) -> None:
        """サマリーレコードの更新"""
        symbol = dividend_record.symbol or "GENERAL"

        if symbol not in self._summary_records:
            self._summary_records[symbol] = DividendSummaryRecord(
                account_id=dividend_record.account_id,
                symbol=symbol,
                description=dividend_record.description,
            )

        summary = self._summary_records[symbol]
        summary.total_gross_amount += dividend_record.gross_amount
        summary.total_tax_amount += dividend_record.tax_amount

    def get_summary_records(self) -> List[DividendSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)
