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
        self._matured_symbols: set = set()
    
    def process(self, transaction: Transaction) -> None:
        """株式取引トランザクションを処理"""
        # 満期トランザクションのシンボルを記憶し、過去のすべての取引を除外
        if self._is_matured_transaction(transaction):
            self._matured_symbols.add(transaction.symbol)
            # すでに記録された取引から同じシンボルの全ての取引を削除
            self.records = [
                record for record in self.records 
                if record.symbol != transaction.symbol
            ]
            return

        # 満期を迎えたシンボルに属する場合は除外
        if transaction.symbol in self._matured_symbols:
            return

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