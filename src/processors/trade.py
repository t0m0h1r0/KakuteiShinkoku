from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional, List, Tuple
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
    
    def __init__(self, symbol: str, premium: Decimal, fees: Decimal, 
                 quantity: int, open_date: date):
        self.symbol = symbol
        self.premium = premium            # 1契約あたりの総プレミアム
        self.fees = fees                  # 1契約あたりの手数料
        self.quantity = quantity
        self.open_date = open_date
        self._net_premium = premium - fees  # 1契約あたりの純プレミアム

    @property
    def total_premium(self) -> Decimal:
        """総プレミアム金額"""
        return self.premium * self.quantity

    @property
    def total_fees(self) -> Decimal:
        """総手数料"""
        return self.fees * self.quantity

    @property
    def net_premium(self) -> Decimal:
        """純プレミアム（手数料控除後）"""
        return self._net_premium

    @property
    def total_net_premium(self) -> Decimal:
        """総純プレミアム（手数料控除後）"""
        return self._net_premium * self.quantity

    def reduce_position(self, quantity: int) -> Tuple[Decimal, Decimal]:
        """ポジションを減少させ、実現損益を返す"""
        if quantity > self.quantity:
            quantity = self.quantity

        realized_premium = self.premium * quantity
        realized_net = self._net_premium * quantity
        self.quantity -= quantity

        return realized_premium, realized_net

class TradeProcessor(BaseProcessor[TradeRecord]):
    """取引処理クラス"""

    def __init__(self, exchange_rate_provider, position_manager: IPositionManager):
        super().__init__(exchange_rate_provider)
        self.position_manager = position_manager
        self.option_premiums = []  # オプションプレミアムの記録用
        self.open_options: Dict[str, OptionPosition] = {}  # オープンポジションの追跡

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """取引関連のトランザクションかどうかを判定"""
        action = transaction.action_type.upper()
        return (action in {'BUY', 'SELL', 'EXPIRED', 'ASSIGNED'} or
                any(action.startswith(prefix) for prefix in 
                    {'SELL_TO_', 'BUY_TO_'}))

    def _process_transaction(self, transaction: Transaction) -> None:
        """取引トランザクションを処理"""
        if not transaction.symbol:
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
        if not transaction.quantity:
            return

        action = transaction.action_type.upper()
        quantity = abs(transaction.quantity)
        price = transaction.price or Decimal('0')
        fees = transaction.fees or Decimal('0')
        
        try:
            # Sell to Open の場合（プレミアム収入）
            if 'SELL TO OPEN' in action:
                premium = abs(transaction.amount)
                net_premium = premium - fees
                
                # オープンポジションとして記録
                self._record_option_open_position(
                    transaction.symbol,
                    net_premium / quantity,
                    quantity,
                    transaction.transaction_date
                )
                
                # 取引記録を生成
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
                    realized_gain=Money(net_premium),
                    cost_basis=Money(Decimal('0')),
                    proceeds=Money(premium),
                    exchange_rate=self._get_exchange_rate(transaction.transaction_date)
                )
                self.records.append(record)
                
                # プレミアム記録を追加
                self._record_premium_transaction(
                    date=transaction.transaction_date,
                    symbol=transaction.symbol,
                    description=transaction.description,
                    premium=premium,
                    fees=fees,
                    action=action,
                    quantity=quantity,
                    status="OPEN"
                )

            # 期限切れまたは権利行使の場合
            elif action in ['EXPIRED', 'ASSIGNED']:
                # 対応するオープンポジションを探す
                base_symbol = self._get_base_symbol(transaction.symbol)
                for open_symbol, position in list(self.open_options.items()):
                    if (self._get_base_symbol(open_symbol) == base_symbol and 
                        position.quantity > 0):
                        
                        realized_premium, net_realized = position.reduce_position(quantity)
                        
                        # 取引記録を生成（決済）
                        record = TradeRecord(
                            trade_date=transaction.transaction_date,
                            account_id=transaction.account_id,
                            symbol=transaction.symbol,
                            description=transaction.description,
                            trade_type='Option',
                            action=action,
                            quantity=quantity,
                            price=Money(Decimal('0')),
                            fees=Money(Decimal('0')),
                            realized_gain=Money(net_realized),
                            cost_basis=Money(Decimal('0')),
                            proceeds=Money(net_realized),
                            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
                        )
                        self.records.append(record)
                        
                        # プレミアム記録を追加（決済）
                        self._record_premium_transaction(
                            date=transaction.transaction_date,
                            symbol=transaction.symbol,
                            description=f"{action}: {transaction.description}",
                            premium=realized_premium,
                            fees=Decimal('0'),
                            action=action,
                            quantity=quantity,
                            status="CLOSED"
                        )
                        
                        if position.quantity <= 0:
                            self.open_options.pop(open_symbol)
                        break

        except Exception as e:
            self._logger.error(f"Error processing option trade: {e}", exc_info=True)
            raise

    def _record_premium_transaction(self, date, symbol, description, 
                                  premium, fees, action, quantity, status):
        """プレミアム取引を記録"""
        self.option_premiums.append({
            'date': date,
            'symbol': symbol,
            'description': description,
            'premium': premium,
            'fees': fees,
            'net_premium': premium - fees,
            'action': action,
            'quantity': quantity,
            'status': status
        })

    def _record_option_open_position(self, symbol: str, premium: Decimal, 
                                   quantity: int, open_date: date) -> None:
        """オプションのオープンポジションを記録"""
        fees = self._calculate_option_fees(quantity)
        
        if symbol in self.open_options:
            existing = self.open_options[symbol]
            # 既存ポジションとマージ
            total_quantity = existing.quantity + quantity
            total_premium = (existing.premium * existing.quantity + premium * quantity)
            total_fees = existing.total_fees + fees
            avg_premium = total_premium / total_quantity
            avg_fees = total_fees / total_quantity
            
            self.open_options[symbol] = OptionPosition(
                symbol=symbol,
                premium=avg_premium,
                fees=avg_fees,
                quantity=total_quantity,
                open_date=open_date
            )
        else:
            self.open_options[symbol] = OptionPosition(
                symbol=symbol,
                premium=premium,
                fees=fees / quantity,
                quantity=quantity,
                open_date=open_date
            )

    def _calculate_option_fees(self, quantity: int) -> Decimal:
        """オプション取引の手数料を計算"""
        base_fee = Decimal('0.65') * quantity  # 基本手数料: $0.65 per contract
        return base_fee

    def get_option_premium_summary(self) -> dict:
        """オプションプレミアムのサマリーを取得"""
        if not self.option_premiums:
            return {
                'total_premium': Decimal('0'),
                'total_fees': Decimal('0'),
                'net_premium': Decimal('0'),
                'realized_premium': Decimal('0'),
                'unrealized_premium': Decimal('0'),
                'transaction_count': 0,
                'average_premium': Decimal('0'),
                'open_positions': 0,
                'total_contracts': 0,
                'expired_contracts': 0,
                'assigned_contracts': 0,
                'active_contracts': 0
            }

        total_premium = Decimal('0')
        total_fees = Decimal('0')
        realized_premium = Decimal('0')
        unrealized_premium = Decimal('0')
        expired_contracts = 0
        assigned_contracts = 0
        total_contracts = 0

        # トランザクション別の集計
        for record in self.option_premiums:
            total_fees += record['fees']
            total_contracts += record['quantity']

            if record['status'] == 'OPEN':
                if 'SELL TO OPEN' in record['action']:
                    total_premium += record['premium']
                    unrealized_premium += record['net_premium']
            else:  # CLOSED
                if record['action'] == 'EXPIRED':
                    expired_contracts += record['quantity']
                    realized_premium += record['net_premium']
                elif record['action'] == 'ASSIGNED':
                    assigned_contracts += record['quantity']
                    realized_premium += record['net_premium']

        transaction_count = len([r for r in self.option_premiums 
                               if 'SELL TO OPEN' in r['action']])
        active_contracts = sum(pos.quantity for pos in self.open_options.values())

        return {
            'total_premium': total_premium,
            'total_fees': total_fees,
            'net_premium': realized_premium + unrealized_premium,
            'realized_premium': realized_premium,
            'unrealized_premium': unrealized_premium,
            'transaction_count': transaction_count,
            'average_premium': ((realized_premium + unrealized_premium) / 
                              transaction_count if transaction_count > 0 else Decimal('0')),
            'open_positions': len(self.open_options),
            'total_contracts': total_contracts,
            'expired_contracts': expired_contracts,
            'assigned_contracts': assigned_contracts,
            'active_contracts': active_contracts
        }

    def get_option_premium_records(self) -> List[dict]:
        """オプションプレミアムの詳細記録を取得"""
        records = sorted(self.option_premiums, key=lambda x: x['date'])
        
        # 累積の実現/未実現損益を計算
        cumulative_realized = Decimal('0')
        cumulative_unrealized = Decimal('0')
        
        for record in records:
            if record['status'] == 'OPEN':
                cumulative_unrealized += record['net_premium']
            else:  # CLOSED
                cumulative_realized += record['net_premium']
                cumulative_unrealized -= (record['premium'] - record['fees'])
            
            # 累積値を記録に追加
            record['cumulative_realized'] = cumulative_realized
            record['cumulative_unrealized'] = cumulative_unrealized
            record['cumulative_total'] = cumulative_realized + cumulative_unrealized
        
        return records

    def _get_base_symbol(self, option_symbol: str) -> str:
        """オプションシンボルから基本シンボルを抽出"""
        return option_symbol.split()[0] if option_symbol else ""

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