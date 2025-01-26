from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import date
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Currency
from ...exchange.exchange import exchange
from .record import StockTradeRecord, StockSummaryRecord
from .position import StockLot, StockPosition
from .tracker import StockTransactionTracker
from .config import StockProcessingConfig

class StockProcessor(BaseProcessor):
    """株式取引処理のメインプロセッサ"""
    def __init__(self):
        super().__init__()
        self._positions: Dict[str, StockPosition] = {}
        self._trade_records: List[StockTradeRecord] = []
        self._summary_records: Dict[str, StockSummaryRecord] = {}
        self._transaction_tracker = StockTransactionTracker()
        self._matured_symbols: set = set()
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_all(self, transactions: List[Transaction]) -> List[StockTradeRecord]:
        """全トランザクションを処理"""
        try:
            self.logger.debug("トランザクションの追跡を開始")
            self._transaction_tracker.track_daily_transactions(transactions)
            
            for symbol, daily_symbol_txs in self._transaction_tracker._daily_transactions.items():
                sorted_dates = sorted(daily_symbol_txs.keys())
                for transaction_date in sorted_dates:
                    transactions_on_date = daily_symbol_txs[transaction_date]
                    self._process_daily_transactions(symbol, transactions_on_date)

            self.logger.info(f"合計 {len(self._trade_records)} の株式取引レコードを処理")
            return self._trade_records

        except Exception as e:
            self.logger.error(f"株式取引処理中にエラーが発生: {e}")
            return []

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理"""
        try:
            if not transaction.symbol:
                return

            if self._transaction_tracker.is_matured(transaction.symbol, transaction.transaction_date):
                if transaction.symbol not in self._matured_symbols:
                    self._handle_maturity(transaction.symbol)
                return

            if not self._is_stock_transaction(transaction):
                return

            self._process_stock_transaction(transaction)

        except Exception as e:
            self.logger.error(f"株式取引の処理中にエラー: {transaction} - {e}")

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        # 満期チェック
        if any(self._transaction_tracker.is_matured(symbol, t.transaction_date) for t in transactions):
            if symbol not in self._matured_symbols:
                self._handle_maturity(symbol)
            return

        # 株式取引の処理
        stock_transactions = [t for t in transactions if self._is_stock_transaction(t)]
        for transaction in stock_transactions:
            self._process_stock_transaction(transaction)

    def _process_stock_transaction(self, transaction: Transaction) -> None:
        """株式取引の詳細処理"""
        try:
            symbol = transaction.symbol
            action = transaction.action_type.upper()
            quantity = Decimal(str(transaction.quantity or 0))
            price = Decimal(str(transaction.price or 0))
            fees = Decimal(str(transaction.fees or 0))
            
            # ポジション更新と損益計算
            realized_gain, avg_price, position = self._update_position(
                symbol, action, quantity, price, fees
            )
            
            # 取引レコードの作成
            record = self._create_trade_record(
                transaction, symbol, action, quantity, 
                price, fees, realized_gain, avg_price
            )
            
            self._trade_records.append(record)
            self._update_summary_record(record, position)
            
            # トラッカーの更新
            self._transaction_tracker.update_tracking(
                symbol,
                quantity if action == 'BUY' else -quantity,
                price * quantity,
                realized_gain
            )

        except Exception as e:
            self.logger.error(f"株式取引処理中にエラー: {e}")
            raise

    def _handle_maturity(self, symbol: str) -> None:
        """満期処理"""
        self._matured_symbols.add(symbol)
        if symbol in self._positions:
            del self._positions[symbol]
        self._trade_records = [r for r in self._trade_records if r.symbol != symbol]

    def _update_position(
        self, 
        symbol: str, 
        action: str, 
        quantity: Decimal, 
        price: Decimal, 
        fees: Decimal
    ) -> Tuple[Decimal, Decimal, StockPosition]:
        """ポジションの更新"""
        position = self._positions.get(symbol, StockPosition())
        self._positions[symbol] = position
        
        if action == 'BUY':
            position.add_lot(StockLot(quantity, price, fees))
            realized_gain = Decimal('0')
        elif action == 'SELL':
            realized_gain = position.remove_shares(quantity, price, fees)
        else:
            raise ValueError(f"Invalid action: {action}")
        
        avg_price = position.average_price
        return realized_gain, avg_price, position

    def _create_trade_record(
        self, 
        transaction: Transaction,
        symbol: str,
        action: str,
        quantity: Decimal,
        price: Decimal,
        fees: Decimal,
        realized_gain: Decimal,
        avg_price: Decimal
    ) -> StockTradeRecord:
        """トレードレコードの作成"""
        price_money = self._create_money(price * quantity)
        gain_money = self._create_money(realized_gain)
        fees_money = self._create_money(fees)
        
        return StockTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=price_money,
            realized_gain=gain_money,
            fees=fees_money,
            exchange_rate=exchange.get_rate(Currency.USD, Currency.JPY, transaction.transaction_date).rate,
        )

    def _update_summary_record(self, record: StockTradeRecord, position: StockPosition) -> None:
        """サマリーレコードの更新"""
        summary = self._summary_records.get(record.symbol)
        if not summary:
            summary = StockSummaryRecord(
                record.account_id,
                record.symbol,
                record.description,
                record.trade_date,
                record.quantity
            )
            self._summary_records[record.symbol] = summary
        
        summary.total_realized_gain += record.realized_gain
        summary.total_fees += record.fees
        summary.remaining_quantity = position.total_quantity
        
        if position.total_quantity == 0:
            summary.close_date = record.trade_date

    @staticmethod        
    def _is_stock_transaction(transaction: Transaction) -> bool: 
        """株式トランザクションの判定"""
        return transaction.action_type.upper() in StockProcessingConfig.STOCK_ACTIONS

    def get_records(self) -> List[StockTradeRecord]:
        """トレードレコードの取得"""
        return sorted(self._trade_records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[StockSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)