from decimal import Decimal
from typing import Dict, List
from collections import defaultdict
import re
from datetime import date

from ..core.transaction import Transaction
from ..exchange.money import Money
from ..exchange.currency import Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .stock_records import StockTradeRecord, StockSummaryRecord
from .stock_lot import StockLot, StockPosition

class StockProcessor(BaseProcessor):
    """株式取引処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._positions: Dict[str, StockPosition] = defaultdict(StockPosition)
        self._trade_records: List[StockTradeRecord] = []
        self._summary_records: Dict[str, StockSummaryRecord] = {}
        self._matured_symbols: set = set()

    def process(self, transaction: Transaction) -> None:
        """取引の処理"""
        # 満期トランザクションのシンボルを記憶し、過去のすべての取引を除外
        if self._is_matured_transaction(transaction):
            self._matured_symbols.add(transaction.symbol)
            # すでに記録された取引から同じシンボルの全ての取引を削除
            self._trade_records = [
                record for record in self._trade_records 
                if record.symbol != transaction.symbol
            ]
            return

        # 満期を迎えたシンボルに属する場合は除外
        if transaction.symbol in self._matured_symbols:
            return

        if not self._is_stock_transaction(transaction):
            return
    
        self._process_stock_transaction(transaction)

    def _process_stock_transaction(self, transaction: Transaction) -> None:
        """株式取引を処理"""
        symbol = transaction.symbol
        action = transaction.action_type.upper()
        quantity = self._parse_decimal(transaction.quantity)
        price = self._parse_decimal(transaction.price)
        fees = self._parse_decimal(transaction.fees)
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)
        
        position = self._positions[symbol]
        realized_gain = Decimal('0')
        
        if action == 'BUY':
            # 買い取引
            lot = StockLot(
                trade_date=transaction.transaction_date,
                quantity=quantity,
                price=price,
                fees=fees
            )
            position.add_lot(lot)
        elif action == 'SELL':
            # 売り取引
            realized_gain = position.sell_shares(quantity, price, fees)
    
        # 金額オブジェクトの作成
        price_money = self._create_money_with_rate(price * quantity, exchange_rate)
        fees_money = self._create_money_with_rate(fees, exchange_rate)
        realized_gain_money = self._create_money_with_rate(realized_gain, exchange_rate)

        # 取引記録の作成
        trade_record = StockTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=price_money,
            realized_gain=realized_gain_money,
            fees=fees_money,
            exchange_rate=exchange_rate
        )
        
        self._trade_records.append(trade_record)
        self._update_summary_record(trade_record, position)

    def _update_summary_record(self, trade_record: StockTradeRecord, 
                             position: StockPosition) -> None:
        """サマリーレコードを更新"""
        symbol = trade_record.symbol
        
        # サマリーレコードが存在しない場合は作成
        if symbol not in self._summary_records:
            self._summary_records[symbol] = StockSummaryRecord(
                account_id=trade_record.account_id,
                symbol=symbol,
                description=trade_record.description,
                open_date=trade_record.trade_date,
                initial_quantity=trade_record.quantity,
                exchange_rate=trade_record.exchange_rate
            )
        
        summary = self._summary_records[symbol]
        position_summary = position.get_position_summary()
        realized_gains = position.get_realized_gains()
        
        # ポジション情報の更新
        summary.remaining_quantity = position_summary['quantity']
        if not position_summary['has_position']:
            summary.status = 'Closed'
            summary.close_date = trade_record.trade_date
        
        # 損益情報の更新
        summary.total_realized_gain = self._create_money_with_rate(
            realized_gains['total_realized_gain'], 
            trade_record.exchange_rate
        )
        summary.total_fees = self._create_money_with_rate(
            realized_gains['total_fees'], 
            trade_record.exchange_rate
        )

    def _is_stock_transaction(self, transaction: Transaction) -> bool:
        """株式取引トランザクションかどうかを判定"""
        if not transaction.symbol:
            return False
        
        stock_actions = {'BUY', 'SELL'}
        return (
            transaction.action_type.upper() in stock_actions and
            not self._is_option_symbol(transaction.symbol)
        )
    
    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))
    
    def _is_matured_transaction(self, transaction: Transaction) -> bool:
        """満期トランザクションかどうかを判定"""
        maturity_keywords = [
            'MATURITY', 
            'MATURED', 
            'CD MATURITY', 
            'BOND MATURITY', 
            'CD DEPOSIT FUNDS',
            'CD DEPOSIT ADJ',
            'FULL REDEMPTION'
        ]
        return transaction.action_type.upper() in [keyword.upper() for keyword in maturity_keywords]

    @staticmethod
    def _parse_decimal(value: any) -> Decimal:
        """数値をDecimalに変換"""
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        elif isinstance(value, str):
            return Decimal(value.replace('$', '').replace(',', '').strip())
        return Decimal('0')