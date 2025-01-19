import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import OptionTradeRecord, StockTradeRecord
from .stock_trade import StockTradeProcessor

class OptionPosition:
    """オプションポジション管理クラス"""
    def __init__(self):
        self.long_positions = 0    # 買建玉数
        self.short_positions = 0   # 売建玉数
        self.open_trades = []      # オープンポジションの記録
        self.closed_trades = []    # クローズされた取引の記録
        self.premium_trades = []   # 期日到来で精算された取引の記録

    def add_trade(self, trade):
        """取引を追加し、ポジションを更新"""
        trade_type = 'LONG' if trade['action'] == 'BUY_TO_OPEN' else 'SHORT'
        quantity = trade['quantity']
        premium = -trade['premium'] if trade_type == 'LONG' else trade['premium']

        if trade_type == 'LONG':
            self.long_positions += quantity
        else:
            self.short_positions += quantity

        self.open_trades.append({
            'type': trade_type,
            'quantity': quantity,
            'premium': premium,
            'date': trade['date']
        })

    def close_position(self, trade):
        """反対売買によるクローズ処理"""
        is_buy_to_close = trade['action'] == 'BUY_TO_CLOSE'
        positions_to_check = self.short_positions if is_buy_to_close else self.long_positions
        target_type = 'SHORT' if is_buy_to_close else 'LONG'
        remaining_quantity = trade['quantity']

        if positions_to_check <= 0:
            return

        # ポジションの更新
        if is_buy_to_close:
            self.short_positions -= trade['quantity']
        else:
            self.long_positions -= trade['quantity']

        # FIFOでクローズ処理
        for open_trade in self.open_trades:
            if remaining_quantity <= 0:
                break

            if open_trade['type'] == target_type and open_trade['quantity'] > 0:
                close_qty = min(remaining_quantity, open_trade['quantity'])
                premium_multiplier = close_qty / open_trade['quantity']
                close_premium_multiplier = close_qty / trade['quantity']
                
                # プレミアムの計算（符号の調整）
                close_premium = (-trade['premium'] if is_buy_to_close else trade['premium']) * close_premium_multiplier

                # 譲渡損益を記録
                self.closed_trades.append({
                    'open_date': open_trade['date'],
                    'close_date': trade['date'],
                    'quantity': close_qty,
                    'open_premium': open_trade['premium'] * premium_multiplier,
                    'close_premium': close_premium
                })

                open_trade['quantity'] -= close_qty
                remaining_quantity -= close_qty

    def handle_expiration(self, expiry_date):
        """期限到来時の処理"""
        remaining_longs = self.long_positions
        remaining_shorts = self.short_positions

        if remaining_longs == 0 and remaining_shorts == 0:
            return

        # 期限到来時のプレミアム損益を計算
        for trade in self.open_trades:
            if trade['quantity'] > 0:  # 未決済分がある場合
                self.premium_trades.append({
                    'open_date': trade['date'],
                    'expire_date': expiry_date,
                    'quantity': trade['quantity'],
                    'premium': trade['premium'],
                    'type': trade['type']
                })
                
                if trade['type'] == 'LONG':
                    self.long_positions -= trade['quantity']
                else:
                    self.short_positions -= trade['quantity']
                trade['quantity'] = 0

    def calculate_gains(self):
        """損益計算"""
        trading_gains = Decimal('0')  # 譲渡損益
        premium_gains = Decimal('0')  # プレミアム損益

        # 反対売買による譲渡損益の計算
        for trade in self.closed_trades:
            trading_gains += trade['close_premium'] + trade['open_premium']

        # 期限到来によるプレミアム損益の計算
        for trade in self.premium_trades:
            premium_gains += trade['premium']

        return {
            'trading_gains': trading_gains.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'premium_gains': premium_gains.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        }

    def get_position_status(self):
        """現在のポジション状況を取得"""
        return {
            'long_positions': self.long_positions,
            'short_positions': self.short_positions,
            'has_open_positions': self.long_positions > 0 or self.short_positions > 0
        }

@dataclass
class OptionLot:
    """オプション取引ロットを表すクラス"""
    symbol: str
    quantity: int
    price: Decimal
    open_date: date
    fees: Decimal
    position_type: str  # 'Long' or 'Short'
    exchange_rate: Decimal  # 為替レート

class OptionTradeProcessor(BaseProcessor[OptionTradeRecord]):
    """オプション取引の処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider, stock_processor: StockTradeProcessor):
        super().__init__(exchange_rate_provider)
        self.stock_processor = stock_processor
        self._positions: Dict[str, OptionPosition] = defaultdict(OptionPosition)

    def process(self, transaction: Transaction) -> None:
        """オプション取引トランザクションを処理"""
        if not self._is_option_trade(transaction):
            return

        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        action = transaction.action_type.upper()
        position = self._positions[transaction.symbol]
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)

        quantity = abs(int(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))

        # 取引情報の作成
        trade_info = {
            'action': action,
            'quantity': quantity,
            'premium': price,
            'date': transaction.transaction_date
        }

        if action in ['BUY_TO_OPEN', 'SELL_TO_OPEN']:
            position.add_trade(trade_info)
        elif action in ['BUY_TO_CLOSE', 'SELL_TO_CLOSE']:
            position.close_position(trade_info)
        elif action == 'EXPIRED':
            position.handle_expiration(transaction.transaction_date)

        # 損益の計算
        gains = position.calculate_gains()
        
        # 為替レート付きでMoneyオブジェクトを作成
        trading_gains_money = self._create_money_with_rate(gains['trading_gains'], exchange_rate)
        premium_gains_money = self._create_money_with_rate(gains['premium_gains'], exchange_rate)

        trade_record = OptionTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=self._create_money_with_rate(price, exchange_rate),
            fees=self._create_money_with_rate(fees, exchange_rate),
            exchange_rate=exchange_rate,
            expiry_date=option_info['expiry_date'],
            strike_price=option_info['strike_price'],
            option_type=option_info['option_type'],
            position_type=self._determine_position_type(action),
            is_expired=(action == 'EXPIRED'),
            trading_gains=trading_gains_money,
            premium_gains=premium_gains_money
        )
        
        self.records.append(trade_record)

    def _is_option_trade(self, transaction: Transaction) -> bool:
        """オプション取引トランザクションかどうかを判定"""
        option_actions = {
            'BUY_TO_OPEN', 'SELL_TO_OPEN', 
            'BUY_TO_CLOSE', 'SELL_TO_CLOSE',
            'EXPIRED', 'ASSIGNED'
        }
        return (
            transaction.action_type.upper() in option_actions and
            self._is_option_symbol(transaction.symbol)
        )

    def _determine_position_type(self, action: str) -> str:
        """ポジションタイプを判定"""
        if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE']:
            return 'Long'
        return 'Short'

    # 以下のメソッドは既存のまま
    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))

    def _parse_option_info(self, symbol: str) -> Optional[Dict]:
        """オプションシンボルを解析"""
        try:
            pattern = r'(\w+)\s+(\d{2}/\d{2}/\d{4})\s+(\d+\.\d+)\s+([CP])'
            match = re.match(pattern, symbol)
            if match:
                underlying, expiry, strike, option_type = match.groups()
                return {
                    'underlying': underlying,
                    'expiry_date': expiry,
                    'strike_price': Decimal(strike),
                    'option_type': option_type
                }
        except (ValueError, AttributeError):
            return None