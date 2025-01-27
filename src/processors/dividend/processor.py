"""
配当処理モジュール

このモジュールは、配当金に関連する取引の処理を行います。
配当の種類（現金配当、再投資配当）や税金処理を含む、
配当に関連する全ての処理を管理します。
"""

from typing import List, Dict, Optional
from decimal import Decimal
import logging
from datetime import date

from ...core.tx import Transaction
from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.processor import BaseProcessor
from ...core.error import ProcessingError

from .record import DividendTradeRecord, DividendSummaryRecord
from .tracker import DividendTransactionTracker
from .config import DividendActionTypes, DividendTypes

class DividendProcessor(BaseProcessor[DividendTradeRecord, DividendSummaryRecord]):
    """配当処理クラス
    
    配当金取引の処理と記録を管理します。
    税金処理や配当の種類（現金、再投資）に応じた処理を行います。
    
    Attributes:
        _transaction_tracker: 配当取引の追跡管理
        _record_class: 取引記録クラス
        _summary_class: サマリー記録クラス
        logger: ロガーインスタンス
    """
    
    def __init__(self) -> None:
        """初期化処理"""
        super().__init__()
        self._transaction_tracker = DividendTransactionTracker()
        self._record_class = DividendTradeRecord
        self._summary_class = DividendSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次取引の処理
        
        同一銘柄の同一日付の取引をまとめて処理します。
        税金処理を優先的に行い、その後配当処理を実行します。
        
        Args:
            symbol: 処理対象の銘柄
            transactions: 処理対象のトランザクションリスト
        """
        # 税金取引の優先処理
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_tx in tax_transactions:
            self._process_tax(tax_tx)

        # 配当取引の処理
        dividend_transactions = [t for t in transactions if self._is_dividend_transaction(t)]
        for transaction in dividend_transactions:
            self.process(transaction)

    def process(self, transaction: Transaction) -> None:
        """配当取引の処理
        
        配当取引の内容を解析し、適切な処理を行います。
        取引記録の作成と保存、サマリー情報の更新を行います。
        
        Args:
            transaction: 処理対象の配当トランザクション
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            if not self._is_dividend_transaction(transaction):
                return

            # 取引情報の解析と作成
            trade_info = self._analyze_dividend_transaction(transaction)
            if not trade_info:
                return

            # 取引記録の作成
            record = self._create_trade_record(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                description=transaction.description,
                action_type=transaction.action_type,
                income_type=self._determine_dividend_type(transaction),
                **trade_info
            )
            
            # 記録の保存と更新
            self._save_and_update_records(record)
            
            # トラッキング情報の更新
            self._update_tracking_info(record)

        except Exception as e:
            self.logger.error(f"配当処理中にエラー: {e}")
            raise ProcessingError(f"配当処理に失敗: {e}")

    def _analyze_dividend_transaction(
        self, 
        transaction: Transaction
    ) -> Optional[Dict]:
        """配当取引の解析
        
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

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当取引の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            配当取引の場合True
        """
        action = transaction.action_type.upper()
        return (
            action in DividendActionTypes.VALID_ACTIONS and 
            abs(transaction.amount) > 0
        )

    def _determine_dividend_type(self, transaction: Transaction) -> str:
        """配当種類の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            配当種類を示す文字列
        """
        return (
            DividendTypes.REINVESTED 
            if 'REINVEST' in transaction.action_type.upper() 
            else DividendTypes.CASH
        )

    def _save_and_update_records(self, dividend_record: DividendTradeRecord) -> None:
        """記録の保存と更新
        
        Args:
            dividend_record: 保存する配当取引記録
        """
        # 取引記録の保存
        self._trade_records.append(dividend_record)
        
        # サマリー記録の更新
        self._update_summary_record(dividend_record)
        
    def _update_summary_record(self, dividend_record: DividendTradeRecord) -> None:
        """サマリー記録の更新
        
        Args:
            dividend_record: 更新の基となる配当取引記録
        """
        symbol = dividend_record.symbol or 'GENERAL'
        
        if symbol not in self._summary_records:
            self._summary_records[symbol] = self._create_summary_record(
                account_id=dividend_record.account_id,
                symbol=symbol,
                description=dividend_record.description,
                open_date=dividend_record.record_date
            )
        
        summary = self._summary_records[symbol]
        summary.total_gross_amount += dividend_record.gross_amount
        summary.total_tax_amount += dividend_record.tax_amount

    def _update_tracking_info(self, record: DividendTradeRecord) -> None:
        """トラッキング情報の更新
        
        Args:
            record: 更新の基となる配当取引記録
        """
        self._transaction_tracker.update_tracking(
            record.symbol, 
            record.gross_amount.usd, 
            record.tax_amount.usd
        )

    def get_summary_records(self) -> List[DividendSummaryRecord]:
        """サマリー記録の取得
        
        Returns:
            銘柄でソートされたサマリー記録のリスト
        """
        return sorted(
            self._summary_records.values(), 
            key=lambda x: x.symbol
        )