from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional
import re
import logging

from src.core.models import Transaction, TradeRecord, Position, Money
from src.core.interfaces import IPositionManager
from src.config.constants import OptionType, Currency
from src.config.action_types import ActionTypes
from .base import BaseProcessor

class PositionManager(IPositionManager):
    """ポジション管理クラス"""
    
    def __init__(self):
        self._positions: Dict[str, Position] = {}
        self._logger = logging.getLogger(self.__class__.__name__)

    def update_position(self, transaction: Transaction) -> None:
        """ポジションを更新"""
        if not transaction.symbol:
            return

        action = transaction.action_type.upper()
        quantity = transaction.quantity or Decimal('0')
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')

        if action == 'BUY':
            self._handle_buy(transaction.symbol, quantity, price, fees)
        elif action == 'SELL':
            self._handle_sell(transaction.symbol, quantity)

    def _handle_buy(self, symbol: str, quantity: Decimal, 
                   price: Decimal, fees: Decimal) -> None:
        """買付の処理"""
        cost = quantity * price + fees
        
        if symbol in self._positions:
            # 既存ポジションの更新
            current = self._positions[symbol]
            new_quantity = current.quantity + quantity
            new_cost = current.cost_basis.amount + cost
            
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=new_quantity,
                cost_basis=Money(new_cost)
            )
        else:
            # 新規ポジションの作成
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                cost_basis=Money(cost)
            )

    def _handle_sell(self, symbol: str, quantity: Decimal) -> None:
        """売却の処理"""
        if symbol not in self._positions:
            self._logger.warning(f"No position found for {symbol}")
            return

        current = self._positions[symbol]
        new_quantity = current.quantity - quantity

        if new_quantity <= 0:
            # ポジション解消
            del self._positions[symbol]
        else:
            # ポジション減少
            new_cost = current.cost_basis.amount * (new_quantity / current.quantity)
            self._positions[symbol] = Position(
                symbol=symbol,
                quantity=new_quantity,
                cost_basis=Money(new_cost)
            )

    def get_position(self, symbol: str) -> Optional[Position]:
        """現在のポジションを取得"""
        return self._positions.get(symbol)

class TradeProcessor(BaseProcessor[TradeRecord]):
    """取引処理クラス"""

    def __init__(self, exchange_rate_provider, position_manager: IPositionManager):
        super().__init__(exchange_rate_provider)
        self.position_manager = position_manager

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """取引関連のトランザクションかどうかを判定"""
        action = transaction.action_type.upper()  # 大文字に変換して比較
        return (action in {'BUY', 'SELL', 'EXPIRED', 'ASSIGNED'} or
                any(action.startswith(prefix) for prefix in 
                    {'SELL_TO_', 'BUY_TO_'}))

    def _process_transaction(self, transaction: Transaction) -> None:
        """取引トランザクションを処理"""
        if not transaction.symbol:  # シンボルが空の場合はスキップ
            return

        try:
            if self._is_option_symbol(transaction.symbol):
                self._process_option_trade(transaction)
            else:
                self._process_stock_trade(transaction)
        except Exception as e:
            self._logger.error(f"Trade processing error: {e}", exc_info=True)
            raise

    def _process_stock_trade(self, transaction: Transaction) -> None:
        """株式取引を処理"""
        if not self._validate_stock_trade(transaction):
            return

        quantity = transaction.quantity
        price = transaction.price
        fees = transaction.fees or Decimal('0')

        # 取引記録の作成
        record = TradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            trade_type='Stock',
            action=transaction.action_type,
            quantity=quantity,
            price=Money(price),
            fees=Money(fees),
            realized_gain=Money(Decimal('0')),  # 後で更新
            cost_basis=Money(Decimal('0')),     # 後で更新
            proceeds=Money(Decimal('0')),       # 後で更新
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )

        # ポジション情報を取得（売却の場合）
        if transaction.action_type.upper() == 'SELL':
            position = self.position_manager.get_position(transaction.symbol)
            if position:
                proceeds = quantity * price - fees
                cost_basis = quantity * position.average_cost.amount
                realized_gain = proceeds - cost_basis

                record = TradeRecord(
                    **{**record.__dict__,
                       'realized_gain': Money(realized_gain),
                       'cost_basis': Money(cost_basis),
                       'proceeds': Money(proceeds)}
                )

        self.records.append(record)
        self.position_manager.update_position(transaction)

    def _process_option_trade(self, transaction: Transaction) -> None:
        """オプション取引を処理"""
        if not transaction.quantity:  # 数量が無い場合はスキップ
            return

        action = transaction.action_type.upper()
        quantity = transaction.quantity
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')

        # 取引記録の作成
        record = TradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            trade_type='Option',
            action=action,
            quantity=quantity,
            price=Money(price),
            fees=Money(fees),
            realized_gain=Money(Decimal('0')),  # オプションの場合は別途計算
            cost_basis=Money(Decimal('0')),
            proceeds=Money(Decimal('0')),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )

        self.records.append(record)

    @staticmethod
    def _is_option_symbol(symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        return bool(re.search(r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]', symbol))

    @staticmethod
    def _validate_stock_trade(transaction: Transaction) -> bool:
        """株式取引のバリデーション"""
        return bool(
            transaction.quantity and
            transaction.quantity != 0 and
            transaction.price and
            transaction.price != 0
        )