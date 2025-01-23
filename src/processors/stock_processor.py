from decimal import Decimal
from typing import Dict, List
from collections import defaultdict

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency
from .base import BaseProcessor
from .stock_records import StockTradeRecord, StockSummaryRecord
from .stock_lot import StockLot, StockPosition

class StockProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self._positions: Dict[str, StockPosition] = defaultdict(StockPosition)
        self._records: List[StockTradeRecord] = []
        self._summary_records: Dict[str, StockSummaryRecord] = {}
        self._matured_symbols: set = set()

    def process(self, transaction: Transaction) -> None:
        if self._is_matured_transaction(transaction):
            self._matured_symbols.add(transaction.symbol)
            self._records = [r for r in self._records if r.symbol != transaction.symbol]
            return
    
        if transaction.symbol in self._matured_symbols:
            return
    
        if self._is_stock_transaction(transaction):
            self._process_stock_transaction(transaction)
    
    def _process_stock_transaction(self, transaction: Transaction) -> None:
        symbol = transaction.symbol
        action = transaction.action_type.upper()
        quantity = Decimal(str(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))
        
        realized_gain, avg_price, position = self._update_position(
            symbol, action, quantity, price, fees
        )
        
        record = StockTradeRecord(
            transaction.transaction_date,
            transaction.account_id,
            symbol,
            transaction.description,
            action,
            quantity,
            self._to_money(price * quantity), 
            self._to_money(realized_gain),
            self._to_money(fees),
            Money(1).as_currency(Currency.JPY),
        )
        self._records.append(record)
        self._update_summary_record(record, position)
    
    def _update_position(self, symbol, action, quantity, price, fees):
        position = self._positions[symbol]
        
        if action == 'BUY':
            position.add_lot(StockLot(quantity, price, fees))
            realized_gain = Decimal('0')
        elif action == 'SELL':
            realized_gain = position.remove_shares(quantity, price, fees)
        else:
            raise ValueError(f"Invalid action: {action}")
        
        avg_price = position.average_price
        return realized_gain, avg_price, position
    
    def _update_summary_record(self, record, position):
        summary = self._summary_records.get(record.symbol)
        if not summary:
            summary = StockSummaryRecord(
                record.account_id, 
                record.symbol, 
                record.description, 
                record.trade_date,
                record.quantity,
                record.exchange_rate,
            )
            self._summary_records[record.symbol] = summary
        
        summary.total_realized_gain += record.realized_gain
        summary.total_fees += record.fees
        summary.remaining_quantity = position.total_quantity
        
        if position.total_quantity == 0:
            summary.close_date = record.trade_date
    
    @staticmethod        
    def _is_stock_transaction(transaction):
        return transaction.action_type.upper() in {'BUY', 'SELL'}
    
    @staticmethod
    def _is_matured_transaction(transaction):
        return 'MATURED' in transaction.description.upper()
        
    def get_records(self) -> List[StockTradeRecord]:
        return sorted(self._records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[StockSummaryRecord]:
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)

    def _to_money(self, amount):
        return Money(amount)