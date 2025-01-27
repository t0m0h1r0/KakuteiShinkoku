from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency

from .record import StockTradeRecord, StockSummaryRecord
from .position import StockLot, StockPosition
from .tracker import StockTransactionTracker
from .config import StockProcessingConfig

class StockProcessor(BaseProcessor[StockTradeRecord, StockSummaryRecord]):
    """株式処理クラス"""
    
    def __init__(self) -> None:
        super().__init__()
        self._positions: Dict[str, StockPosition] = {}
        self._matured_symbols: set = set()
        self._transaction_tracker = StockTransactionTracker()
        self._record_class = StockTradeRecord
        self._summary_class = StockSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, transaction: Transaction) -> None:
        """株式取引の処理"""
        try:
            if not self._is_stock_transaction(transaction):
                return

            if self._transaction_tracker.is_matured(transaction.symbol, transaction.transaction_date):
                if transaction.symbol not in self._matured_symbols:
                    self._handle_maturity(transaction.symbol)
                return

            self._process_stock_transaction(transaction)

        except Exception as e:
            self.logger.error(f"株式取引の処理中にエラー: {transaction} - {e}")

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        if self._check_and_handle_maturity(symbol, transactions):
            return

        stock_transactions = [t for t in transactions if self._is_stock_transaction(t)]
        for transaction in sorted(stock_transactions, key=lambda x: x.transaction_date):
            self._process_stock_transaction(transaction)

    def _check_and_handle_maturity(self, symbol: str, transactions: List[Transaction]) -> bool:
        """満期チェックと処理"""
        if any(self._transaction_tracker.is_matured(symbol, t.transaction_date) for t in transactions):
            if symbol not in self._matured_symbols:
                self._handle_maturity(symbol)
            return True
        return False

    def _process_stock_transaction(self, transaction: Transaction) -> None:
        """株式取引の処理"""
        try:
            symbol = transaction.symbol
            action = transaction.action_type.upper()
            quantity = Decimal(str(transaction.quantity or 0))
            price = Decimal(str(transaction.price or 0))
            fees = Decimal(str(transaction.fees or 0))
            
            # ポジション更新と損益計算
            realized_gain, position = self._update_position_and_calculate_pnl(
                symbol, action, quantity, price, fees
            )
            
            # Money オブジェクトの作成
            trade_money = self._create_trade_money(transaction, quantity, price, realized_gain, fees)
            
            # 取引レコードの作成
            record = self._create_trade_record(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=symbol,
                description=transaction.description,
                action=action,
                quantity=quantity,
                price=trade_money['price'],
                realized_gain=trade_money['realized_gain'],
                fees=trade_money['fees'],
                exchange_rate=trade_money['price'].get_rate()
            )
            
            # レコードの保存と更新
            self._save_and_update_records(record, position)
            
            # トラッキング情報の更新
            self._update_tracking(record, price, realized_gain)

        except Exception as e:
            self.logger.error(f"株式取引処理中にエラー: {e}")
            raise

    def _update_position_and_calculate_pnl(
        self, 
        symbol: str, 
        action: str, 
        quantity: Decimal, 
        price: Decimal, 
        fees: Decimal
    ) -> Tuple[Decimal, StockPosition]:
        """ポジション更新と損益計算"""
        position = self._get_or_create_position(symbol)
        
        if action == 'BUY':
            position.add_lot(StockLot(quantity, price, fees))
            realized_gain = Decimal('0')
        elif action == 'SELL':
            realized_gain = position.remove_shares(quantity, price, fees)
        else:
            raise ValueError(f"不正なアクション: {action}")
        
        return realized_gain, position

    def _create_trade_money(
        self, 
        transaction: Transaction, 
        quantity: Decimal, 
        price: Decimal, 
        realized_gain: Decimal, 
        fees: Decimal
    ) -> Dict[str, Money]:
        """取引関連のMoneyオブジェクトを作成"""
        return {
            'price': self._create_money(price * quantity, transaction.transaction_date),
            'realized_gain': self._create_money(realized_gain, transaction.transaction_date),
            'fees': self._create_money(fees, transaction.transaction_date)
        }

    def _save_and_update_records(self, record: StockTradeRecord, position: StockPosition) -> None:
        """レコードの保存と更新"""
        self._trade_records.append(record)
        self._update_summary_record(record, position)

    def _update_tracking(self, record: StockTradeRecord, price: Decimal, realized_gain: Decimal) -> None:
        """トラッキング情報の更新"""
        self._transaction_tracker.update_tracking(
            record.symbol,
            record.quantity if record.action == 'BUY' else -record.quantity,
            price * record.quantity,
            realized_gain
        )

    def _get_or_create_position(self, symbol: str) -> StockPosition:
        """ポジションの取得または作成"""
        if symbol not in self._positions:
            self._positions[symbol] = StockPosition()
        return self._positions[symbol]

    def _handle_maturity(self, symbol: str) -> None:
        """満期処理"""
        self._matured_symbols.add(symbol)
        if symbol in self._positions:
            del self._positions[symbol]
        self._trade_records = [r for r in self._trade_records if r.symbol != symbol]

    def _update_summary_record(self, record: StockTradeRecord, position: StockPosition) -> None:
        """サマリーレコードの更新"""
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

    @staticmethod
    def _is_stock_transaction(transaction: Transaction) -> bool:
        """株式取引の判定"""
        return (transaction.action_type.upper() in StockProcessingConfig.STOCK_ACTIONS and 
                transaction.symbol is not None)

    def get_summary_records(self) -> List[StockSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)