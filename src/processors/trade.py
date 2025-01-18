from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional, List
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

class OptionPosition:
    """オプションポジション管理クラス"""
    
    def __init__(self, symbol: str, premium: Decimal, quantity: int):
        self.symbol = symbol
        self.premium = premium
        self.quantity = quantity
        self.open_date = datetime.now().date()

    @property
    def total_premium(self) -> Decimal:
        """総プレミアム金額"""
        return self.premium * self.quantity

class TradeProcessor(BaseProcessor[TradeRecord]):
    """取引処理クラス"""

    def __init__(self, exchange_rate_provider, position_manager: IPositionManager):
        super().__init__(exchange_rate_provider)
        self.position_manager = position_manager
        self.option_premiums = []  # オプションプレミアムの記録用
        self.open_options: Dict[str, OptionPosition] = {}  # オープンポジションの追跡

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
            realized_gain=Money(Decimal('0')),
            cost_basis=Money(Decimal('0')),
            proceeds=Money(Decimal('0')),
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
        quantity = abs(transaction.quantity)
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')
        premium = Decimal('0')

        # Sell to Open の場合
        if 'SELL TO OPEN' in action:
            premium = abs(transaction.amount)
            net_premium = premium - fees
            
            # オープンポジションとして記録
            self._record_option_open_position(
                transaction.symbol,
                net_premium / quantity,  # 1契約あたりのプレミアム
                quantity
            )
            
            # プレミアム記録に追加
            self.option_premiums.append({
                'date': transaction.transaction_date,
                'symbol': transaction.symbol,
                'description': transaction.description,
                'premium': premium,
                'fees': fees,
                'action': action,
                'quantity': quantity
            })

        # 期限切れまたは権利行使の場合
        elif action in ['EXPIRED', 'ASSIGNED']:
            # symbol をキーとしてオープンポジションを検索
            base_symbol = self._get_base_symbol(transaction.symbol)
            for open_symbol in list(self.open_options.keys()):
                if self._get_base_symbol(open_symbol) == base_symbol:
                    position = self.open_options[open_symbol]
                    premium = position.premium * quantity
                    
                    # プレミアム記録に追加
                    self.option_premiums.append({
                        'date': transaction.transaction_date,
                        'symbol': transaction.symbol,
                        'description': transaction.description,
                        'premium': premium,
                        'fees': fees,
                        'action': action,
                        'quantity': quantity
                    })
                    
                    # ポジションを更新
                    self._close_option_position(open_symbol, quantity)
                    break

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
            realized_gain=Money(premium),
            cost_basis=Money(Decimal('0')),
            proceeds=Money(premium),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )

        self.records.append(record)

    def _get_base_symbol(self, option_symbol: str) -> str:
        """オプションシンボルから基本シンボルを抽出"""
        return option_symbol.split()[0] if option_symbol else ""

    def _record_option_open_position(self, symbol: str, premium: Decimal, quantity: int) -> None:
        """オプションのオープンポジションを記録"""
        if symbol in self.open_options:
            existing = self.open_options[symbol]
            # 既存ポジションとマージ
            total_quantity = existing.quantity + quantity
            total_premium = (existing.premium * existing.quantity + premium * quantity)
            avg_premium = total_premium / total_quantity
            self.open_options[symbol] = OptionPosition(
                symbol=symbol,
                premium=avg_premium,
                quantity=total_quantity
            )
        else:
            self.open_options[symbol] = OptionPosition(
                symbol=symbol,
                premium=premium,
                quantity=quantity
            )

    def _close_option_position(self, symbol: str, quantity: int) -> None:
        """オプションポジションをクローズ"""
        if symbol in self.open_options:
            position = self.open_options[symbol]
            position.quantity -= quantity
            if position.quantity <= 0:
                del self.open_options[symbol]
                
    def get_option_premium_summary(self) -> dict:
        """オプションプレミアムのサマリーを取得"""
        if not self.option_premiums:
            return {
                'total_premium': Decimal('0'),
                'total_fees': Decimal('0'),
                'net_premium': Decimal('0'),
                'transaction_count': 0,
                'average_premium': Decimal('0'),
                'open_positions': 0
            }

        total_premium = sum(p['premium'] for p in self.option_premiums)
        total_fees = sum(p['fees'] for p in self.option_premiums)
        transaction_count = len(self.option_premiums)

        return {
            'total_premium': total_premium,
            'total_fees': total_fees,
            'net_premium': total_premium - total_fees,
            'transaction_count': transaction_count,
            'average_premium': (total_premium - total_fees) / transaction_count
            if transaction_count > 0 else Decimal('0'),
            'open_positions': len(self.open_options)
        }

    def get_option_premium_records(self) -> List[dict]:
        """オプションプレミアムの詳細記録を取得"""
        return sorted(self.option_premiums, key=lambda x: x['date'])

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