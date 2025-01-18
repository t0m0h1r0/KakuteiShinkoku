from decimal import Decimal
from typing import List
import re

from .base import BaseProcessor
from src.core.types.transaction import Transaction
from src.core.types.money import Money
from src.core.interfaces import IExchangeRateProvider

class TradeRecord:
    def __init__(
        self, 
        trade_date,
        account_id: str,
        symbol: str,
        description: str,
        trade_type: str,
        action: str,
        quantity: Decimal,
        price: Money,
        fees: Money,
        realized_gain: Money,
        cost_basis: Money,
        proceeds: Money,
        exchange_rate: Decimal,
        holding_period_days: int = None
    ):
        self.trade_date = trade_date
        self.account_id = account_id
        self.symbol = symbol
        self.description = description
        self.trade_type = trade_type
        self.action = action
        self.quantity = quantity
        self.price = price
        self.fees = fees
        self.realized_gain = realized_gain
        self.cost_basis = cost_basis
        self.proceeds = proceeds
        self.exchange_rate = exchange_rate
        self.holding_period_days = holding_period_days

class TradeProcessor(BaseProcessor[TradeRecord]):
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
    
    def process(self, transaction: Transaction) -> None:
        """トランザクションを処理"""
        if self._is_target_transaction(transaction):
            self._process_trade(transaction)

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """取引対象のトランザクションかを判定"""
        trade_actions = {'BUY', 'SELL', 'EXPIRED', 'ASSIGNED'}
        return transaction.action_type.upper() in trade_actions

    def _process_trade(self, transaction: Transaction) -> None:
        """取引を処理"""
        trade_type = 'Stock' if not self._is_option_symbol(transaction.symbol) else 'Option'
        
        trade_record = TradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            trade_type=trade_type,
            action=transaction.action_type,
            quantity=transaction.quantity or Decimal('0'),
            price=Money(transaction.price or Decimal('0')),
            fees=Money(transaction.fees or Decimal('0')),
            realized_gain=Money(Decimal('0')),  # 簡略化のため
            cost_basis=Money(Decimal('0')),     # 簡略化のため
            proceeds=Money(Decimal('0')),       # 簡略化のため
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
        
        self.records.append(trade_record)

    @staticmethod
    def _is_option_symbol(symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))
