import re
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict
from datetime import date

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import OptionTradeRecord, StockTradeRecord
from .stock_trade import StockTradeProcessor

@dataclass
class OptionLot:
    """オプション取引ロットを表すクラス"""
    symbol: str
    quantity: int
    price: Decimal
    open_date: date
    fees: Decimal
    position_type: str  # 'Long' or 'Short'

class OptionPosition:
    """オプションポジション管理クラス"""
    def __init__(self):
        self.lots: List[OptionLot] = []
        self.reversed_trades: List[Dict] = []  # 逆順取引を一時的に保存
    
    def add_lot(self, lot: OptionLot):
        """ロットを追加"""
        self.lots.append(lot)
    
    def close_position(self, quantity: int, price: Decimal, fees: Decimal, 
                      is_buy_to_close: bool, trade_date: date) -> Decimal:
        """ポジションをクローズし損益を計算（FIFO）"""
        # 対応するオープンポジションが存在しない場合
        if not self.lots:
            # 逆順取引として記録
            self.reversed_trades.append({
                'quantity': quantity,
                'price': price,
                'fees': fees,
                'is_buy_to_close': is_buy_to_close,
                'date': trade_date
            })
            return Decimal('0')  # 損益は後で計算
        
        remaining_quantity = quantity
        realized_gain = Decimal('0')
        
        while remaining_quantity > 0 and self.lots:
            lot = self.lots[0]
            
            # クローズする数量を決定
            close_quantity = min(remaining_quantity, lot.quantity)
            quantity_ratio = Decimal(close_quantity) / Decimal(lot.quantity)
            
            # 損益計算
            if lot.position_type == 'Long':
                # Long position
                cost_basis = lot.price * close_quantity + lot.fees * quantity_ratio
                sale_proceed = price * close_quantity - fees * quantity_ratio
                realized_gain += sale_proceed - cost_basis
            else:
                # Short position
                if is_buy_to_close:
                    original_credit = lot.price * close_quantity - lot.fees * quantity_ratio
                    closing_debit = price * close_quantity + fees * quantity_ratio
                    realized_gain += original_credit - closing_debit
            
            # ロットの更新
            if close_quantity == lot.quantity:
                self.lots.pop(0)
            else:
                lot.quantity -= close_quantity
                lot.fees -= lot.fees * quantity_ratio
            
            remaining_quantity -= close_quantity
        
        return realized_gain

    def match_reversed_trades(self) -> List[Dict]:
        """逆順取引のマッチングと損益計算"""
        realized_gains = []
        
        # Buy to OpenとSell to Closeの組み合わせを探す
        while self.reversed_trades:
            trade = self.reversed_trades[0]
            matching_trades = [
                t for t in self.reversed_trades[1:]
                if ((trade['is_buy_to_close'] and not t['is_buy_to_close']) or
                    (not trade['is_buy_to_close'] and t['is_buy_to_close']))
            ]
            
            if matching_trades:
                # マッチする取引を見つけた場合
                matching_trade = matching_trades[0]
                
                # 損益を計算
                if trade['is_buy_to_close']:
                    buy_trade = trade
                    sell_trade = matching_trade
                else:
                    buy_trade = matching_trade
                    sell_trade = trade
                
                # 最小の数量を使用
                quantity = min(trade['quantity'], matching_trade['quantity'])
                
                # 損益計算
                cost_basis = buy_trade['price'] * quantity + buy_trade['fees']
                sale_proceed = sell_trade['price'] * quantity - sell_trade['fees']
                realized_gain = sale_proceed - cost_basis
                
                realized_gains.append({
                    'date': max(trade['date'], matching_trade['date']),
                    'gain': realized_gain,
                    'quantity': quantity
                })
                
                # 使用した数量を更新
                trade['quantity'] -= quantity
                matching_trade['quantity'] -= quantity
                
                # 数量が0になった取引を削除
                self.reversed_trades = [
                    t for t in self.reversed_trades 
                    if t['quantity'] > 0
                ]
            else:
                # マッチする取引が見つからない場合
                break
        
        return realized_gains

class OptionTradeProcessor(BaseProcessor[OptionTradeRecord]):
    """オプション取引の処理クラス（権利行使連携と損益計算対応）"""
    
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
        realized_gain = Decimal('0')
        position_type = self._determine_position_type(action, option_info['option_type'])

        quantity = abs(int(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))

        if action in ['BUY TO OPEN', 'SELL TO OPEN']:
            # ポジションオープン
            lot = OptionLot(
                symbol=transaction.symbol,
                quantity=quantity,
                price=price,
                open_date=transaction.transaction_date,
                fees=fees,
                position_type=position_type
            )
            position.add_lot(lot)
        elif action in ['BUY TO CLOSE', 'SELL TO CLOSE']:
            # ポジションクローズ
            is_buy_to_close = action == 'BUY TO CLOSE'
            realized_gain = position.close_position(
                quantity, price, fees, is_buy_to_close, 
                transaction.transaction_date
            )
            
            # 逆順取引のマッチングと損益計算
            reversed_gains = position.match_reversed_trades()
            for gain_info in reversed_gains:
                if gain_info['date'] == transaction.transaction_date:
                    realized_gain += gain_info['gain']
        elif action == 'ASSIGNED':
            # 権利行使情報を株式取引プロセッサに連携
            self._handle_assignment(transaction, option_info)
            position.lots = []
        elif action == 'EXPIRED':
            # 期限切れの場合、現在の損益を確定
            position.lots = []

        trade_record = OptionTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=Money(price),
            fees=Money(fees),
            expiry_date=option_info['expiry_date'],
            strike_price=option_info['strike_price'],
            option_type=option_info['option_type'],
            position_type=position_type,
            is_expired=action == 'EXPIRED',
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            realized_gain=Money(realized_gain)
        )
        
        self.records.append(trade_record)

    def _handle_assignment(self, transaction: Transaction, option_info: Dict[str, Any]) -> None:
        """権利行使を処理し、株式取引プロセッサに情報を連携"""
        underlying_symbol = option_info['underlying']
        quantity = abs(int(transaction.quantity or 0))
        strike_price = option_info['strike_price']
        
        self.stock_processor.record_option_assignment(
            symbol=underlying_symbol,
            date=transaction.transaction_date,
            quantity=quantity,
            strike_price=strike_price
        )
    
    def _is_option_trade(self, transaction: Transaction) -> bool:
        """オプション取引トランザクションかどうかを判定"""
        option_actions = {'BUY', 'SELL', 'EXPIRED', 'ASSIGNED', 
                          'BUY TO OPEN', 'SELL TO OPEN', 
                          'BUY TO CLOSE', 'SELL TO CLOSE'}
        return (
            transaction.action_type.upper() in option_actions and
            self._is_option_symbol(transaction.symbol)
        )
    
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
            
    def _determine_position_type(self, action: str, option_type: str) -> str:
        """オプションのポジションタイプを決定"""
        action = action.upper()
        
        if action == 'SELL TO OPEN':
            return 'Short'
        elif action == 'BUY TO OPEN':
            return 'Long'
        elif action == 'SELL TO CLOSE':
            return 'Long'
        elif action == 'BUY TO CLOSE':
            return 'Short'
        
        return 'Long'  # デフォルト値