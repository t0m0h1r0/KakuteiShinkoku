from typing import List, Dict, Optional
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency

from .record import InterestTradeRecord, InterestSummaryRecord
from .tracker import InterestTransactionTracker
from .config import InterestProcessingConfig

class InterestProcessor(BaseProcessor[InterestTradeRecord, InterestSummaryRecord]):
    """利子処理クラス"""
    
    def __init__(self) -> None:
        super().__init__()
        self._transaction_tracker = InterestTransactionTracker()
        self._record_class = InterestTradeRecord
        self._summary_class = InterestSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        # 税金処理を先に実行
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        # 利子処理を実行
        interest_transactions = [t for t in transactions if self._is_interest_transaction(t)]
        for transaction in interest_transactions:
            self.process(transaction)

    def process(self, transaction: Transaction) -> None:
        """利子トランザクションの処理"""
        try:
            if not self._is_interest_transaction(transaction):
                return

            # 関連する税金を検索
            tax_amount = self._find_matching_tax(transaction)
            
            # 利子金額と税金のMoneyオブジェクトを作成
            gross_amount = self._create_money(abs(transaction.amount), transaction.transaction_date)
            tax_money = self._create_money(tax_amount, transaction.transaction_date)

            # 取引レコードを作成
            interest_record = self._create_trade_record(
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
            
            # レコードを保存
            self._trade_records.append(interest_record)
            self._update_summary_record(interest_record)
            
            # トラッキング情報を更新
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
        """利子タイプの判定"""
        action = transaction.action_type.upper()
        
        for key, value in InterestProcessingConfig.INTEREST_TYPES.items():
            if key in action:
                return value
        
        return 'Other Interest'

    def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
        """サマリーレコードの更新"""
        symbol = interest_record.symbol or 'GENERAL'
        
        if symbol not in self._summary_records:
            self._summary_records[symbol] = self._create_summary_record(
                account_id=interest_record.account_id,
                symbol=symbol,
                description=interest_record.description,
                open_date=interest_record.record_date
            )
        
        summary = self._summary_records[symbol]
        summary.total_gross_amount += interest_record.gross_amount
        summary.total_tax_amount += interest_record.tax_amount

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)