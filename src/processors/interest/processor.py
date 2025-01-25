from decimal import Decimal
from typing import Dict, List
import logging

from ...core.transaction import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money, Currency
from .record import InterestTradeRecord, InterestSummaryRecord
from .tracker import InterestTransactionTracker
from .config import InterestProcessingConfig

class InterestProcessor(BaseProcessor):
    """利子処理のメインプロセッサ"""
    def __init__(self):
        super().__init__()
        self._trade_records: List[InterestTradeRecord] = []
        self._summary_records: Dict[str, InterestSummaryRecord] = {}
        self._transaction_tracker = InterestTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_all(self, transactions: List[Transaction]) -> List[InterestTradeRecord]:
        """全トランザクションを処理"""
        try:
            self.logger.debug("トランザクションの追跡を開始")
            self._transaction_tracker.track_daily_transactions(transactions)
            
            for symbol, daily_symbol_txs in self._transaction_tracker._daily_transactions.items():
                sorted_dates = sorted(daily_symbol_txs.keys())
                for transaction_date in sorted_dates:
                    transactions_on_date = daily_symbol_txs[transaction_date]
                    self._process_daily_transactions(symbol, transactions_on_date)

            self.logger.info(f"合計 {len(self._trade_records)} の利子レコードを処理")
            return self._trade_records

        except Exception as e:
            self.logger.error(f"利子取引処理中にエラーが発生: {e}")
            return []

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理"""
        try:
            if self._is_tax_transaction(transaction):
                self._process_tax(transaction)
                return

            if not self._is_interest_transaction(transaction):
                return

            self._process_transaction(transaction)

        except Exception as e:
            self.logger.error(f"利子取引の処理中にエラー: {transaction} - {e}")

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_transaction in tax_transactions:
            self._process_tax(tax_transaction)

        interest_transactions = [t for t in transactions if self._is_interest_transaction(t)]
        for transaction in interest_transactions:
            self._process_transaction(transaction)

    def _process_transaction(self, transaction: Transaction) -> None:
        """利子取引の詳細処理"""
        try:
            tax_amount = self._find_matching_tax(transaction)
            
            gross_amount = self._create_money(abs(transaction.amount))
            tax_money = self._create_money(tax_amount)

            interest_record = self._create_interest_record(
                transaction, gross_amount, tax_money
            )
            
            self._trade_records.append(interest_record)
            self._update_summary_record(interest_record)
            
            self._transaction_tracker.update_tracking(
                transaction.symbol or 'GENERAL',
                abs(transaction.amount),
                tax_amount
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

    def _create_interest_record(
        self, 
        transaction: Transaction, 
        gross_amount: Money,
        tax_amount: Money
    ) -> InterestTradeRecord:
        """利子レコードの作成"""
        return InterestTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type=self._determine_interest_type(transaction),
            action_type=transaction.action_type,
            gross_amount=gross_amount,
            tax_amount=tax_amount,
            exchange_rate=self._rate_provider.get_rate(Currency.USD, Currency.JPY, transaction.transaction_date).rate,
        )

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
                              
    def get_records(self) -> List[InterestTradeRecord]:
        """トレードレコードの取得"""
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)