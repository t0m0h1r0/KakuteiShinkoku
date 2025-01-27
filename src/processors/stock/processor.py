"""
株式取引処理モジュール

このモジュールは、株式取引に関する処理を行います。
ポジション管理、損益計算、取引履歴の管理など、
株式取引に必要な全ての機能を提供します。
"""

from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency
from ...core.error import ProcessingError

from .record import StockTradeRecord, StockSummaryRecord
from .position import StockLot, StockPosition
from .tracker import StockTransactionTracker
from .config import StockProcessingConfig

class StockProcessor(BaseProcessor[StockTradeRecord, StockSummaryRecord]):
    """株式取引処理クラス
    
    株式取引の処理と記録を管理します。
    FIFOベースのポジション管理と損益計算を行います。
    
    Attributes:
        _positions: 銘柄ごとのポジション管理
        _matured_symbols: 満期/消滅した銘柄セット
        _transaction_tracker: 取引追跡管理
        _record_class: 取引記録クラス
        _summary_class: サマリー記録クラス
        logger: ロガーインスタンス
    """
    
    def __init__(self) -> None:
        """初期化処理"""
        super().__init__()
        self._positions: Dict[str, StockPosition] = {}
        self._matured_symbols: set = set()
        self._transaction_tracker = StockTransactionTracker()
        self._record_class = StockTradeRecord
        self._summary_class = StockSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次取引の処理
        
        同一銘柄の同一日付の取引をまとめて処理します。
        満期チェックを行い、有効な取引のみを処理します。
        
        Args:
            symbol: 処理対象の銘柄
            transactions: 処理対象のトランザクションリスト
        """
        if self._check_and_handle_maturity(symbol, transactions):
            return

        stock_transactions = [t for t in transactions if self._is_stock_transaction(t)]
        for transaction in sorted(stock_transactions, key=lambda x: x.transaction_date):
            self._process_stock_transaction(transaction)

    def process(self, transaction: Transaction) -> None:
        """株式取引の処理
        
        トランザクションの内容を解析し、適切な処理を行います。
        
        Args:
            transaction: 処理対象のトランザクション
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            if not self._is_stock_transaction(transaction):
                return

            # 満期チェック
            if self._transaction_tracker.is_matured(transaction.symbol, transaction.transaction_date):
                if transaction.symbol not in self._matured_symbols:
                    self._handle_maturity(transaction.symbol)
                return

            self._process_stock_transaction(transaction)

        except Exception as e:
            self.logger.error(f"株式取引処理中にエラー: {e}")
            raise ProcessingError(f"株式取引処理に失敗: {e}")

    def _process_stock_transaction(self, transaction: Transaction) -> None:
        """株式取引の実際の処理
        
        取引内容に応じてポジション更新と損益計算を行います。
        
        Args:
            transaction: 処理対象の株式トランザクション
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            # 取引情報の解析
            trade_info = self._analyze_stock_transaction(transaction)
            if not trade_info:
                return

            # ポジション更新と損益計算
            pnl_info = self._update_position_and_calculate_pnl(
                transaction.symbol, 
                trade_info
            )

            # Money オブジェクトの作成
            money_values = self._create_trade_money(
                transaction, 
                trade_info, 
                pnl_info
            )

            # 取引記録の作成
            record = self._create_trade_record(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                description=transaction.description,
                action=trade_info['action'],
                quantity=trade_info['quantity'],
                price=money_values['price'],
                realized_gain=money_values['realized_gain'],
                fees=money_values['fees'],
                exchange_rate=money_values['price'].get_rate()
            )

            # 記録の保存と更新
            self._save_and_update_records(
                record, 
                self._positions[transaction.symbol]
            )

            # トラッキング情報の更新
            self._update_tracking_info(record, trade_info, pnl_info)

        except Exception as e:
            self.logger.error(f"取引処理中にエラー: {e}")
            raise ProcessingError(f"取引処理に失敗: {e}")

    def _analyze_stock_transaction(
        self, 
        transaction: Transaction
    ) -> Optional[Dict]:
        """株式取引の解析
        
        Args:
            transaction: 解析対象のトランザクション
            
        Returns:
            解析結果の辞書（取引情報）
        """
        try:
            return {
                'action': transaction.action_type.upper(),
                'quantity': Decimal(str(transaction.quantity or 0)),
                'price': Decimal(str(transaction.price or 0)),
                'fees': Decimal(str(transaction.fees or 0))
            }
        except Exception as e:
            self.logger.error(f"取引解析エラー: {e}")
            return None

    def _update_position_and_calculate_pnl(
        self, 
        symbol: str, 
        trade_info: Dict
    ) -> Dict:
        """ポジション更新と損益計算
        
        Args:
            symbol: 対象銘柄
            trade_info: 取引情報
            
        Returns:
            損益情報を含む辞書
        """
        position = self._get_or_create_position(symbol)
        
        if trade_info['action'] == 'BUY':
            position.add_lot(StockLot(
                trade_info['quantity'],
                trade_info['price'],
                trade_info['fees']
            ))
            realized_gain = Decimal('0')
        else:  # SELL
            realized_gain = position.remove_shares(
                trade_info['quantity'],
                trade_info['price'],
                trade_info['fees']
            )
        
        return {
            'realized_gain': realized_gain,
            'position': position
        }

    def _create_trade_money(
        self, 
        transaction: Transaction,
        trade_info: Dict,
        pnl_info: Dict
    ) -> Dict[str, Money]:
        """取引金額のMoney オブジェクト作成
        
        Args:
            transaction: 対象トランザクション
            trade_info: 取引情報
            pnl_info: 損益情報
            
        Returns:
            Money オブジェクトの辞書
        """
        return {
            'price': self._create_money(
                trade_info['price'] * trade_info['quantity'],
                transaction.transaction_date
            ),
            'realized_gain': self._create_money(
                pnl_info['realized_gain'],
                transaction.transaction_date
            ),
            'fees': self._create_money(
                trade_info['fees'],
                transaction.transaction_date
            )
        }

    def _get_or_create_position(self, symbol: str) -> StockPosition:
        """ポジションの取得または作成
        
        Args:
            symbol: 対象銘柄
            
        Returns:
            対象銘柄のポジション
        """
        if symbol not in self._positions:
            self._positions[symbol] = StockPosition()
        return self._positions[symbol]

    def _check_and_handle_maturity(
        self, 
        symbol: str, 
        transactions: List[Transaction]
    ) -> bool:
        """満期チェックと処理
        
        Args:
            symbol: 対象銘柄
            transactions: 対象トランザクションリスト
            
        Returns:
            満期処理を行った場合True
        """
        if any(self._transaction_tracker.is_matured(symbol, t.transaction_date) 
               for t in transactions):
            if symbol not in self._matured_symbols:
                self._handle_maturity(symbol)
            return True
        return False

    def _handle_maturity(self, symbol: str) -> None:
        """満期処理
        
        Args:
            symbol: 対象銘柄
        """
        self._matured_symbols.add(symbol)
        if symbol in self._positions:
            del self._positions[symbol]
        self._trade_records = [r for r in self._trade_records if r.symbol != symbol]

    def _save_and_update_records(
        self,
        record: StockTradeRecord,
        position: StockPosition
    ) -> None:
        """記録の保存と更新
        
        Args:
            record: 保存する取引記録
            position: 対応するポジション
        """
        self._trade_records.append(record)
        self._update_summary_record(record, position)

    def _update_summary_record(
        self,
        record: StockTradeRecord,
        position: StockPosition
    ) -> None:
        """サマリー記録の更新
        
        Args:
            record: 更新の基となる取引記録
            position: 対応するポジション
        """
        if record.symbol not in self._summary_records:
            self._summary_records[record.symbol] = self._create_summary_record(
                account_id=record.account_id,
                symbol=record.symbol,
                description=record.description,
                open_date=record.record_date,
                initial_quantity=record.quantity
            )
        
        summary = self._summary_records[record.symbol]
        summary.total_realized_gain += record.realized_gain
        summary.total_fees += record.fees
        summary.remaining_quantity = position.total_quantity
        
        if position.total_quantity == 0:
            summary.close_date = record.record_date
            summary.status = 'Closed'

    def _update_tracking_info(
        self,
        record: StockTradeRecord,
        trade_info: Dict,
        pnl_info: Dict
    ) -> None:
        """トラッキング情報の更新
        
        Args:
            record: 対象取引記録
            trade_info: 取引情報
            pnl_info: 損益情報
        """
        self._transaction_tracker.update_tracking(
            record.symbol,
            trade_info['quantity'] if trade_info['action'] == 'BUY' else -trade_info['quantity'],
            trade_info['price'] * trade_info['quantity'],
            pnl_info['realized_gain']
        )

    @staticmethod
    def _is_stock_transaction(transaction: Transaction) -> bool:
        """株式取引の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            株式取引の場合True
        """
        return (
            transaction.action_type.upper() in StockProcessingConfig.STOCK_ACTIONS and 
            transaction.symbol is not None
        )

    def get_summary_records(self) -> List[StockSummaryRecord]:
        """サマリー記録の取得
        
        Returns:
            銘柄でソートされたサマリー記録のリスト
        """
        return sorted(
            self._summary_records.values(),
            key=lambda x: x.symbol
        )