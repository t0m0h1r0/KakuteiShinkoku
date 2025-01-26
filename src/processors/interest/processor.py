from typing import Dict, List
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency

from .record import InterestTradeRecord, InterestSummaryRecord
from .tracker import InterestTransactionTracker
from .config import InterestProcessingConfig

class InterestProcessor(BaseProcessor[InterestTradeRecord]):
    def __init__(self):
        super().__init__()
        self._summary_records: Dict[str, InterestSummaryRecord] = {}
        self._transaction_tracker = InterestTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションを処理"""
        # 税金トランザクションの処理
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        # 利子トランザクションの処理
        interest_transactions = [
            t for t in transactions 
            if self._is_interest_transaction(t)
        ]
        for transaction in interest_transactions:
            self._process_transaction(transaction)

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションを処理"""
        try:
            if self._is_tax_transaction(transaction):
                self._process_tax(transaction)
                return

            if not self._is_interest_transaction(transaction):
                return

            self._process_transaction(transaction)
        except Exception as e:
            self.logger.error(f"利子取引の処理中にエラー: {transaction} - {e}")

    def _process_transaction(self, transaction: Transaction) -> None:
        """利子トランザクションの処理"""
        try:
            # 税金の検索
            tax_amount = self._find_matching_tax(transaction)
            
            # Money オブジェクトを使用
            gross_amount = Money(abs(transaction.amount), Currency.USD, transaction.transaction_date)
            tax_money = Money(tax_amount, Currency.USD, transaction.transaction_date)

            interest_record = InterestTradeRecord(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol or '',
                description=transaction.description,
                action_type=transaction.action_type,
                income_type=self._determine_interest_type(transaction),
                gross_amount=gross_amount,
                tax_amount=tax_money,
                exchange_rate=gross_amount.get_rate()
            )
            
            self._trade_records.append(interest_record)
            self._update_summary_record(interest_record)
            
            self._transaction_tracker.update_tracking(
                transaction.symbol or 'GENERAL',
                gross_amount.usd,
                tax_money.usd
            )

        except Exception as e:
            self.logger.error(f"利子取引処理中にエラー: {e}")
            raise

    def _is_interest_transaction(self, transaction: Transaction) -> bool:
        """利子トランザクションの判定"""
        return (
            transaction.action_type.upper() in InterestProcessingConfig.INTEREST_ACTIONS and 
            abs(transaction.amount) > InterestProcessingConfig.MINIMUM_TAXABLE_INTEREST
        )

    def _determine_interest_type(self, transaction: Transaction) -> str:
        """利子の種類を決定"""
        action = transaction.action_type.upper()
        
        for key, value in InterestProcessingConfig.INTEREST_TYPES.items():
            if key in action:
                return value
        
        return 'Other Interest'

    def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
        """サマリーレコードの更新"""
        symbol = interest_record.symbol or 'GENERAL'
        
        if symbol not in self._summary_records:
            self._summary_records[symbol] = InterestSummaryRecord(
                account_id=interest_record.account_id,
                symbol=symbol,
                description=interest_record.description,
            )
        
        summary = self._summary_records[symbol]
        summary.total_gross_amount += interest_record.gross_amount
        summary.total_tax_amount += interest_record.tax_amount

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)