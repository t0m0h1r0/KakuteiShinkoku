from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional
import re

from src.core.models import Transaction, TradeRecord, Position, Money
from src.core.interfaces import IPositionManager
from src.config.constants import OptionType, Currency
from src.config.action_types import ActionTypes
from .base import BaseProcessor

@dataclass
class OptionContract:
    """オプション契約情報"""
    underlying: str
    expiry_date: date
    strike_price: Decimal
    option_type: str
    
    @property
    def full_symbol(self) -> str:
        """完全なオプションシンボル"""
        return (f"{self.underlying} {self.expiry_date.strftime('%m/%d/%Y')} "
                f"{self.strike_price:.2f} {self.option_type}")

    @classmethod
    def from_symbol(cls, symbol: str) -> Optional['OptionContract']:
        """シンボルからオプション契約を生成"""
        pattern = r"([A-Z]+)\s+(\d{2}/\d{2}/\d{4})\s+(\d+\.\d{2})\s+([CP])"
        if match := re.match(pattern, symbol):
            return cls(
                underlying=match.group(1),
                expiry_date=datetime.strptime(match.group(2), '%m/%d/%Y').date(),
                strike_price=Decimal(match.group(3)),
                option_type=match.group(4)
            )
        return None

class PositionManager(IPositionManager):
    """ポジション管理クラス"""
    
    def __init__(self):
        self._stock_positions: Dict[str, Position] = {}
        self._option_positions: Dict[str, Position] = {}

    def update_position(self, transaction: Transaction) -> None:
        """ポジションを更新"""
        if transaction.action_type in ActionTypes.OPTION_ACTIONS:
            self._update_option_position(transaction)
        elif transaction.action_type in ActionTypes.STOCK_ACTIONS:
            self._update_stock_position(transaction)

    def get_position(self, symbol: str) -> Optional[Position]:
        """現在のポジションを取得"""
        return (self._option_positions.get(symbol) or 
                self._stock_positions.get(symbol))

    def _update_stock_position(self, transaction: Transaction) -> None:
        """株式ポジションを更新"""
        quantity = transaction.quantity or Decimal('0')
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')
        
        if transaction.action_type == 'BUY':
            cost = quantity * price + fees
            self._add_to_position(
                self._stock_positions,
                transaction.symbol,
                quantity,
                Money(cost)
            )
        else:  # SELL
            self._remove_from_position(
                self._stock_positions,
                transaction.symbol,
                quantity
            )

    def _update_option_position(self, transaction: Transaction) -> None:
        """オプションポジションを更新"""
        contract = OptionContract.from_symbol(transaction.symbol)
        if not contract:
            return

        quantity = transaction.quantity or Decimal('0')
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')
        
        if ActionTypes.is_opening_action(transaction.action_type):
            cost = quantity * price * Decimal('100') + fees
            self._add_to_position(
                self._option_positions,
                contract.full_symbol,
                quantity,
                Money(cost)
            )
        else:
            self._remove_from_position(
                self._option_positions,
                contract.full_symbol,
                quantity
            )

    def _add_to_position(self, positions: Dict[str, Position],
                        symbol: str, quantity: Decimal, cost: Money) -> None:
        """ポジションを追加"""
        if symbol not in positions:
            positions[symbol] = Position(symbol, quantity, cost)
        else:
            pos = positions[symbol]
            positions[symbol] = Position(
                symbol,
                pos.quantity + quantity,
                Money(pos.cost_basis.amount + cost.amount)
            )

    def _remove_from_position(self, positions: Dict[str, Position],
                            symbol: str, quantity: Decimal) -> None:
        """ポジションを削減"""
        if symbol in positions:
            pos = positions[symbol]
            remaining_quantity = pos.quantity - quantity
            
            if remaining_quantity > 0:
                remaining_cost = pos.cost_basis.amount * (remaining_quantity / pos.quantity)
                positions[symbol] = Position(
                    symbol,
                    remaining_quantity,
                    Money(remaining_cost)
                )
            else:
                del positions[symbol]

class TradeProcessor(BaseProcessor[TradeRecord]):
    """取引処理クラス"""

    def __init__(self, exchange_rate_provider, position_manager: PositionManager):
        super().__init__(exchange_rate_provider)
        self.position_manager = position_manager

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """取引関連のトランザクションかどうかを判定"""
        return (transaction.action_type in ActionTypes.OPTION_ACTIONS or
                transaction.action_type in ActionTypes.STOCK_ACTIONS)

    def _process_transaction(self, transaction: Transaction) -> None:
        """取引トランザクションを処理"""
        try:
            if transaction.action_type in ActionTypes.OPTION_ACTIONS:
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

        # ポジション情報を取得
        position = self.position_manager.get_position(transaction.symbol)
        
        # 損益計算
        proceeds = quantity * price - fees
        cost_basis = (quantity * position.average_cost.amount 
                     if position else Decimal('0'))
        realized_gain = proceeds - cost_basis

        # 取引記録を作成
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
            realized_gain=Money(realized_gain),
            cost_basis=Money(cost_basis),
            proceeds=Money(proceeds),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
        self.records.append(record)

        # ポジションを更新
        self.position_manager.update_position(transaction)

    def _process_option_trade(self, transaction: Transaction) -> None:
        """オプション取引を処理"""
        contract = OptionContract.from_symbol(transaction.symbol)
        if not contract or not self._validate_option_trade(transaction):
            return

        if transaction.action_type == 'EXPIRED':
            self._handle_option_expiration(contract, transaction)
        elif transaction.action_type == 'ASSIGNED':
            self._handle_option_assignment(contract, transaction)
        else:
            self._handle_normal_option_trade(contract, transaction)

    def _handle_normal_option_trade(self, contract: OptionContract,
                                  transaction: Transaction) -> None:
        """通常のオプション取引を処理"""
        quantity = transaction.quantity
        price = transaction.price
        fees = transaction.fees or Decimal('0')

        position = self.position_manager.get_position(contract.full_symbol)
        
        if ActionTypes.is_opening_action(transaction.action_type):
            # 新規建て
            proceeds = quantity * price * Decimal('100') - fees
            self.records.append(TradeRecord(
                trade_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=contract.full_symbol,
                description=transaction.description,
                trade_type='Option Premium',
                action=transaction.action_type,
                quantity=quantity,
                price=Money(price),
                fees=Money(fees),
                realized_gain=Money(proceeds),
                cost_basis=Money(Decimal('0')),
                proceeds=Money(proceeds),
                exchange_rate=self._get_exchange_rate(transaction.transaction_date)
            ))
        else:
            # 決済
            proceeds = quantity * price * Decimal('100') - fees
            cost_basis = (quantity * position.average_cost.amount 
                         if position else Decimal('0'))
            realized_gain = proceeds - cost_basis

            self.records.append(TradeRecord(
                trade_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=contract.full_symbol,
                description=transaction.description,
                trade_type='Option',
                action=transaction.action_type,
                quantity=quantity,
                price=Money(price),
                fees=Money(fees),
                realized_gain=Money(realized_gain),
                cost_basis=Money(cost_basis),
                proceeds=Money(proceeds),
                exchange_rate=self._get_exchange_rate(transaction.transaction_date)
            ))

        self.position_manager.update_position(transaction)

    def _handle_option_expiration(self, contract: OptionContract,
                                transaction: Transaction) -> None:
        """オプションの満期失効を処理"""
        position = self.position_manager.get_position(contract.full_symbol)
        if not position:
            return

        # 投資額全額が損失
        realized_gain = -position.cost_basis.amount

        self.records.append(TradeRecord(
            trade_date=contract.expiry_date,
            account_id=transaction.account_id,
            symbol=contract.full_symbol,
            description=f"Option Expired - {contract.full_symbol}",
            trade_type='Option',
            action='EXPIRED',
            quantity=position.quantity,
            price=Money(Decimal('0')),
            fees=Money(Decimal('0')),
            realized_gain=Money(realized_gain),
            cost_basis=position.cost_basis,
            proceeds=Money(Decimal('0')),
            exchange_rate=self._get_exchange_rate(contract.expiry_date)
        ))

        # ポジション削除
        self.position_manager.update_position(transaction)

    def _handle_option_assignment(self, contract: OptionContract,
                                transaction: Transaction) -> None:
        """オプションの権利行使/割当を処理"""
        position = self.position_manager.get_position(contract.full_symbol)
        if not position:
            return

        # オプションの損失を記録
        realized_gain = -position.cost_basis.amount

        self.records.append(TradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=contract.full_symbol,
            description=transaction.description,
            trade_type='Option',
            action='ASSIGNED',
            quantity=position.quantity,
            price=Money(contract.strike_price),
            fees=Money(Decimal('0')),
            realized_gain=Money(realized_gain),
            cost_basis=position.cost_basis,
            proceeds=Money(Decimal('0')),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        ))

        # 株式ポジションの調整
        stock_quantity = position.quantity * Decimal('100')
        if contract.option_type == OptionType.CALL:
            # コールオプションの場合は株式売却として処理
            self._process_stock_trade(Transaction(
                transaction_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=contract.underlying,
                description=f"Call Assignment - {contract.full_symbol}",
                amount=-contract.strike_price * stock_quantity,
                action_type='SELL',
                quantity=stock_quantity,
                price=contract.strike_price,
                fees=Decimal('0')
            ))
        else:
            # プットオプションの場合は株式購入として処理
            self._process_stock_trade(Transaction(
                transaction_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=contract.underlying,
                description=f"Put Assignment - {contract.full_symbol}",
                amount=contract.strike_price * stock_quantity,
                action_type='BUY',
                quantity=stock_quantity,
                price=contract.strike_price,
                fees=Decimal('0')
            ))

        # オプションポジション削除
        self.position_manager.update_position(transaction)

    @staticmethod
    def _validate_stock_trade(transaction: Transaction) -> bool:
        """株式取引のバリデーション"""
        return bool(transaction.quantity and transaction.price)

    @staticmethod
    def _validate_option_trade(transaction: Transaction) -> bool:
        """オプション取引のバリデーション"""
        if transaction.action_type in ['EXPIRED', 'ASSIGNED']:
            return True
        return bool(transaction.quantity and transaction.price)
