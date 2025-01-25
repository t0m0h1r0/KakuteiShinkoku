from decimal import Decimal
from typing import Dict, List
import logging

from ...core.transaction import Transaction
from ...exchange.money import Money, Currency
from ..base.processor import BaseProcessor
from .record import DividendTradeRecord, DividendSummaryRecord
from .tracker import DividendTransactionTracker
from .config import DividendProcessingConfig

class DividendProcessor(BaseProcessor):
    """配当処理のメインプロセッサ"""
    def __init__(self):
        super().__init__()
        self._trade_records: List[DividendTradeRecord] = []
        self._summary_records: Dict[str, DividendSummaryRecord] = {}
        self._transaction_tracker = DividendTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_all(self, transactions: List[Transaction]) -> List[DividendTradeRecord]:
        try:
            self.logger.debug("トランザクション追跡を開始")
            self._transaction_tracker.track_daily_transactions(transactions)
            
            for symbol, daily_txs in self._transaction_tracker._daily_transactions.items():
                for date in sorted(daily_txs.keys()):
                    self._process_daily_transactions(symbol, daily_txs[date])

            self.logger.info(f"合計 {len(self._trade_records)} の配当レコードを処理")
            return self._trade_records

        except Exception as e:
            self.logger.error(f"配当取引処理中にエラーが発生: {e}")
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
            self.logger.error(f"配当取引の処理中にエラー: {transaction} - {e}")

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_transaction in tax_transactions:
            self._process_tax(tax_transaction)

        dividend_transactions = [t for t in transactions if self._is_dividend_transaction(t)]
        for transaction in dividend_transactions:
            self._process_transaction(transaction)

    def _process_transaction(self, transaction: Transaction) -> None:
        try:
            tax_amount = self._find_matching_tax(transaction)
            
            gross_amount = self._create_money(abs(transaction.amount))
            tax_money = self._create_money(tax_amount)

            dividend_record = self._create_dividend_record(
                transaction, gross_amount, tax_money
            )
            
            self._trade_records.append(dividend_record)
            self._update_summary_record(dividend_record)
            
            self._transaction_tracker.update_tracking(
                transaction.symbol or 'GENERAL',
                abs(transaction.amount),
                tax_amount
            )

        except Exception as e:
            self.logger.error(f"配当取引処理中にエラー: {e}")
            raise

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当トランザクションの判定""" 
        return (
            transaction.action_type.upper() in DividendProcessingConfig.DIVIDEND_ACTIONS and 
            abs(transaction.amount) > Decimal('0')
        )

    def _determine_dividend_type(self, transaction: Transaction) -> str:
        """配当の種類を決定"""
        action = transaction.action_type.upper()
        
        if 'REINVEST' in action:
            return DividendProcessingConfig.DIVIDEND_TYPES['REINVEST']
        
        # デフォルトは通常の現金配当
        return DividendProcessingConfig.DIVIDEND_TYPES['CASH']

    def _create_dividend_record(
        self, 
        transaction: Transaction, 
        gross_amount: Money,
        tax_amount: Money
    ) -> DividendTradeRecord:
        """配当レコードの作成"""
        return DividendTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type=self._determine_dividend_type(transaction),
            action_type=transaction.action_type,
            gross_amount=gross_amount,
            tax_amount=tax_amount,
            exchange_rate=self._rate_provider.get_rate(Currency.USD, Currency.JPY, transaction.transaction_date).rate,
        )

    def _update_summary_record(self, dividend_record: DividendTradeRecord) -> None:
        """サマリーレコードの更新"""
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
        """トレードレコードの取得"""
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[DividendSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)