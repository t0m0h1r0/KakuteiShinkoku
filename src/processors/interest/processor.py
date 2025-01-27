"""
利子処理モジュール

このモジュールは、利子収入に関連する取引の処理を行います。
預金利子、債券利子、CD利子など、様々な種類の利子収入を
一元的に管理し、記録します。
"""

from typing import List, Dict, Optional
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency
from ...core.error import ProcessingError

from .record import InterestTradeRecord, InterestSummaryRecord
from .tracker import InterestTransactionTracker
from .config import InterestProcessingConfig

class InterestProcessor(BaseProcessor[InterestTradeRecord, InterestSummaryRecord]):
    """利子処理クラス
    
    利子収入取引の処理と記録を管理します。
    預金利子、債券利子、CD利子など、様々な種類の利子収入に対応します。
    
    Attributes:
        _transaction_tracker: 利子取引の追跡管理
        _record_class: 取引記録クラス
        _summary_class: サマリー記録クラス
        logger: ロガーインスタンス
    """
    
    def __init__(self) -> None:
        """初期化処理"""
        super().__init__()
        self._transaction_tracker = InterestTransactionTracker()
        self._record_class = InterestTradeRecord
        self._summary_class = InterestSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次取引の処理
        
        同一商品の同一日付の取引をまとめて処理します。
        税金処理を優先的に行い、その後利子処理を実行します。
        
        Args:
            symbol: 処理対象の商品
            transactions: 処理対象のトランザクションリスト
        """
        # 税金取引の優先処理
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        # 利子取引の処理
        interest_transactions = [t for t in transactions if self._is_interest_transaction(t)]
        for transaction in interest_transactions:
            self.process(transaction)

    def process(self, transaction: Transaction) -> None:
        """利子取引の処理
        
        利子取引の内容を解析し、適切な処理を行います。
        取引記録の作成と保存、サマリー情報の更新を行います。
        
        Args:
            transaction: 処理対象の利子トランザクション
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            if not self._is_interest_transaction(transaction):
                return

            # 取引情報の解析と作成
            trade_info = self._analyze_interest_transaction(transaction)
            if not trade_info:
                return

            # 取引記録の作成
            record = self._create_trade_record(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol or '',
                description=transaction.description,
                action_type=transaction.action_type,
                income_type=self._determine_interest_type(transaction),
                **trade_info
            )
            
            # 記録の保存と更新
            self._save_and_update_records(record)
            
            # トラッキング情報の更新
            self._update_tracking_info(record)

        except Exception as e:
            self.logger.error(f"利子処理中にエラー: {e}")
            raise ProcessingError(f"利子処理に失敗: {e}")

    def _analyze_interest_transaction(
        self, 
        transaction: Transaction
    ) -> Optional[Dict]:
        """利子取引の解析
        
        Args:
            transaction: 解析対象のトランザクション
            
        Returns:
            解析結果の辞書（取引情報）
        """
        try:
            # 関連する税金を検索
            tax_amount = self._find_matching_tax(transaction)
            
            # 金額の計算とMoneyオブジェクトの作成
            gross_amount = self._create_money(
                abs(transaction.amount), 
                transaction.transaction_date
            )
            tax_money = self._create_money(
                tax_amount, 
                transaction.transaction_date
            )

            return {
                'gross_amount': gross_amount,
                'tax_amount': tax_money,
                'exchange_rate': gross_amount.get_rate()
            }
            
        except Exception as e:
            self.logger.error(f"取引解析エラー: {e}")
            return None

    def _is_interest_transaction(self, transaction: Transaction) -> bool:
        """利子取引の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            利子取引の場合True
        """
        return (
            transaction.action_type.upper() in InterestProcessingConfig.INTEREST_ACTIONS and 
            abs(transaction.amount) > InterestProcessingConfig.MINIMUM_TAXABLE_INTEREST
        )

    def _determine_interest_type(self, transaction: Transaction) -> str:
        """利子種類の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            利子種類を示す文字列
        """
        action = transaction.action_type.upper()
        
        for key, value in InterestProcessingConfig.INTEREST_TYPES.items():
            if key in action:
                return value
        
        return 'Other Interest'

    def _save_and_update_records(self, interest_record: InterestTradeRecord) -> None:
        """記録の保存と更新
        
        Args:
            interest_record: 保存する利子取引記録
        """
        # 取引記録の保存
        self._trade_records.append(interest_record)
        
        # サマリー記録の更新
        self._update_summary_record(interest_record)

    def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
        """サマリー記録の更新
        
        Args:
            interest_record: 更新の基となる利子取引記録
        """
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

    def _update_tracking_info(self, record: InterestTradeRecord) -> None:
        """トラッキング情報の更新
        
        Args:
            record: 更新の基となる利子取引記録
        """
        self._transaction_tracker.update_tracking(
            record.symbol or 'GENERAL',
            record.gross_amount.usd,
            record.tax_amount.usd
        )

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリー記録の取得
        
        Returns:
            商品でソートされたサマリー記録のリスト
        """
        return sorted(
            self._summary_records.values(), 
            key=lambda x: x.symbol
        )