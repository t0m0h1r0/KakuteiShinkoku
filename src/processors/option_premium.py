import re
from decimal import Decimal
from typing import Optional, Dict, List
from datetime import date
from dataclasses import dataclass
from collections import defaultdict

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import PremiumRecord, OptionTradeRecord

@dataclass
class OptionPosition:
    """オープンポジションの状態管理"""
    symbol: str
    quantity: int
    open_price: Decimal
    open_date: date
    position_type: str  # 'Long' or 'Short'
    total_cost: Decimal
    fees: Decimal

class OptionPremiumProcessor(BaseProcessor[PremiumRecord]):
    """オプションプレミアム処理クラス（改訂版）"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        # キーはシンボル、値はOptionPosition
        self._open_positions: Dict[str, List[OptionPosition]] = defaultdict(list)
        # プレミアム収支の記録
        self._premium_results: Dict[str, Dict] = defaultdict(lambda: {
            'total_premium': Decimal('0'),
            'closing_cost': Decimal('0'),
            'net_premium': Decimal('0'),
            'assignments': []
        })
    
    def process(self, transaction: Transaction) -> None:
        """オプションプレミアムを処理"""
        if not self._is_option_transaction(transaction):
            return
            
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        action = transaction.action_type.upper()
        
        if action == 'SELL TO OPEN':
            self._process_sell_to_open(transaction, option_info)
        elif action == 'BUY TO OPEN':
            self._process_buy_to_open(transaction, option_info)
        elif action == 'BUY TO CLOSE':
            self._process_buy_to_close(transaction, option_info)
        elif action == 'SELL TO CLOSE':
            self._process_sell_to_close(transaction, option_info)
        elif action == 'EXPIRED':
            self._process_expiration(transaction, option_info)
        elif action == 'ASSIGNED':
            self._process_assignment(transaction, option_info)

    def get_premium_summary(self) -> Dict[str, Dict]:
        """プレミアム収支のサマリーを取得"""
        return self._premium_results

    def _create_premium_record(self, transaction: Transaction, option_info: Dict, amount: Decimal) -> None:
        """プレミアムレコードを作成してリストに追加"""
        premium_record = PremiumRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            expiry_date=option_info['expiry_date'],
            strike_price=option_info['strike_price'],
            option_type=option_info['option_type'],
            premium_amount=Money(amount),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
        self.records.append(premium_record)

    def _process_sell_to_open(self, transaction: Transaction, option_info: Dict) -> None:
        """売りポジションのオープンを処理"""
        position = OptionPosition(
            symbol=transaction.symbol,
            quantity=abs(int(transaction.quantity or 0)),
            open_price=abs(transaction.price or Decimal('0')),
            open_date=transaction.transaction_date,
            position_type='Short',
            total_cost=abs(transaction.amount),
            fees=abs(transaction.fees or Decimal('0'))
        )
        
        self._open_positions[transaction.symbol].append(position)
        
        # プレミアム収入を記録
        result = self._premium_results[transaction.symbol]
        premium_amount = abs(transaction.amount)
        result['total_premium'] += premium_amount

        # プレミアムレコードを作成
        self._create_premium_record(transaction, option_info, premium_amount)

    def _process_buy_to_close(self, transaction: Transaction, option_info: Dict) -> None:
        """売りポジションのクローズを処理"""
        positions = self._open_positions[transaction.symbol]
        if not positions:
            return

        # Short positionsのみを対象に
        short_positions = [p for p in positions if p.position_type == 'Short']
        if not short_positions:
            return

        # クローズコストを記録
        result = self._premium_results[transaction.symbol]
        closing_cost = abs(transaction.amount)
        result['closing_cost'] += closing_cost
        
        # ネットプレミアムを更新
        result['net_premium'] = result['total_premium'] - result['closing_cost']
        
        # ポジションをクローズ
        quantity_to_close = abs(int(transaction.quantity or 0))
        self._close_positions(transaction.symbol, quantity_to_close)

        # プレミアムレコードを作成（マイナス値として）
        self._create_premium_record(transaction, option_info, -closing_cost)

    def _process_expiration(self, transaction: Transaction, option_info: Dict) -> None:
        """オプションの期限切れを処理"""
        self._close_positions(transaction.symbol, None)  # 全ポジションをクローズ

    def _process_assignment(self, transaction: Transaction, option_info: Dict) -> None:
        """権利行使を処理"""
        result = self._premium_results[transaction.symbol]
        result['assignments'].append({
            'date': transaction.transaction_date,
            'symbol': transaction.symbol,
            'quantity': abs(int(transaction.quantity or 0))
        })

        self._close_positions(transaction.symbol, None)

    def _process_buy_to_open(self, transaction: Transaction, option_info: Dict) -> None:
        """買いポジションのオープンを処理"""
        position = OptionPosition(
            symbol=transaction.symbol,
            quantity=abs(int(transaction.quantity or 0)),
            open_price=abs(transaction.price or Decimal('0')),
            open_date=transaction.transaction_date,
            position_type='Long',
            total_cost=abs(transaction.amount),
            fees=abs(transaction.fees or Decimal('0'))
        )
        self._open_positions[transaction.symbol].append(position)

    def _process_sell_to_close(self, transaction: Transaction, option_info: Dict) -> None:
        """買いポジションのクローズを処理"""
        positions = self._open_positions[transaction.symbol]
        if not positions:
            return

        # Long positionsのみを対象に
        long_positions = [p for p in positions if p.position_type == 'Long']
        if not long_positions:
            return

        quantity_to_close = abs(int(transaction.quantity or 0))
        self._close_positions(transaction.symbol, quantity_to_close)

    def _close_positions(self, symbol: str, quantity: Optional[int]) -> None:
        """ポジションをクローズ"""
        if quantity is None:
            # 全ポジションをクローズ
            self._open_positions[symbol] = []
            return

        positions = self._open_positions[symbol]
        remaining_quantity = quantity
        
        while remaining_quantity > 0 and positions:
            position = positions[0]
            if position.quantity <= remaining_quantity:
                remaining_quantity -= position.quantity
                positions.pop(0)
            else:
                position.quantity -= remaining_quantity
                remaining_quantity = 0

        self._open_positions[symbol] = positions

    def _is_option_transaction(self, transaction: Transaction) -> bool:
        """オプション取引かどうかを判定"""
        option_actions = {
            'BUY TO OPEN', 'SELL TO OPEN', 
            'BUY TO CLOSE', 'SELL TO CLOSE',
            'EXPIRED', 'ASSIGNED'
        }
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
            # Example: "U 03/17/2023 30.00 P"
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
            pass
        return None