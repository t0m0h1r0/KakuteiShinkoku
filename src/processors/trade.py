from decimal import Decimal
from typing import List, Optional
from datetime import date
import re

from ..core.types.transaction import Transaction
from ..core.types.money import Money
from .base import BaseProcessor
from ..core.interfaces import IExchangeRateProvider

class TradeRecord:
    """取引記録を表すクラス"""
    def __init__(
        self, 
        trade_date: date,
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
        holding_period_days: Optional[int] = None,
        # オプション取引用の追加属性
        expiry_date: Optional[str] = None,
        strike_price: Optional[Decimal] = None,
        option_type: Optional[str] = None,
        position_type: Optional[str] = None,
        is_expired: Optional[bool] = None,
        premium_or_gain: Optional[Money] = None
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
        
        # オプション取引用の属性
        self.expiry_date = expiry_date
        self.strike_price = strike_price
        self.option_type = option_type
        self.position_type = position_type
        self.is_expired = is_expired
        self.premium_or_gain = premium_or_gain or Money(Decimal('0'))

class TradeProcessor(BaseProcessor[TradeRecord]):
    """取引処理クラス"""
    
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
        is_option = self._is_option_symbol(transaction.symbol)
        trade_type = 'Option' if is_option else 'Stock'
        
        # オプション情報の解析
        option_info = self._parse_option_info(transaction.symbol) if is_option else {}
        
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
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            # オプション情報
            expiry_date=option_info.get('expiry_date'),
            strike_price=option_info.get('strike_price'),
            option_type=option_info.get('option_type'),
            position_type='Short' if 'SELL' in transaction.action_type.upper() else 'Long',
            is_expired=transaction.action_type.upper() == 'EXPIRED',
            premium_or_gain=Money(transaction.amount) if transaction.amount else None
        )
        
        self.records.append(trade_record)

    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))

    def _parse_option_info(self, symbol: str) -> dict:
        """オプションシンボルを解析"""
        try:
            parts = symbol.split()
            # 例: "U 03/17/2023 25.00 P"
            return {
                'base_symbol': parts[0],
                'expiry_date': parts[1],
                'strike_price': Decimal(parts[2]),
                'option_type': parts[3]
            }
        except (IndexError, ValueError):
            return {}