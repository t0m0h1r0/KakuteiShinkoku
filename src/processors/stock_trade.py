import re
from decimal import Decimal

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import StockTradeRecord

class StockTradeProcessor(BaseProcessor[StockTradeRecord]):
    """株式取引の処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
    
    def process(self, transaction: Transaction) -> None:
        """株式取引トランザクションを処理"""
        if not self._is_stock_trade(transaction):
            return
            
        trade_record = StockTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            action=transaction.action_type,
            quantity=transaction.quantity or Decimal('0'),
            price=Money(transaction.price or Decimal('0')),
            fees=Money(transaction.fees or Decimal('0')),
            realized_gain=Money(Decimal('0')),  # 実現損益は別途計算
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
        
        self.records.append(trade_record)
    
    def _is_stock_trade(self, transaction: Transaction) -> bool:
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