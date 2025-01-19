import re
from decimal import Decimal
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict
from datetime import date

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import PremiumRecord

@dataclass
class OptionTransactionSummary:
    """オプション取引のサマリー"""
    sell_to_open_amount: Decimal = Decimal('0')
    buy_to_open_amount: Decimal = Decimal('0')
    buy_to_close_amount: Decimal = Decimal('0')
    sell_to_close_amount: Decimal = Decimal('0')
    open_position_quantity: int = 0
    fees: Decimal = Decimal('0')
    net_premium: Decimal = Decimal('0')
    is_closed: bool = False
    close_date: Optional[date] = None
    status: str = 'OPEN'
    # 日本円での金額を追加
    net_premium_jpy: Decimal = Decimal('0')
    exchange_rate: Optional[Decimal] = None

class OptionPremiumProcessor(BaseProcessor[PremiumRecord]):
    """オプションプレミアム処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._transactions: Dict[str, OptionTransactionSummary] = defaultdict(OptionTransactionSummary)
        self._premium_records: Dict[str, Optional[PremiumRecord]] = {}
        self._assignments: Dict[str, List[Dict]] = defaultdict(list)

    def get_assignments(self) -> Dict[str, List[Dict]]:
        """権利行使情報を取得"""
        return self._assignments

    def process(self, transaction: Transaction) -> None:
        """オプションプレミアムを処理"""
        if not self._is_option_transaction(transaction):
            return

        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        action = transaction.action_type.upper()
        amount = abs(transaction.amount or Decimal('0'))
        fees = abs(transaction.fees or Decimal('0'))
        quantity = abs(int(transaction.quantity or 0))
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)

        summary = self._transactions[transaction.symbol]
        summary.exchange_rate = exchange_rate  # 為替レートを保存
        
        # アクションに応じた処理
        if action == 'SELL TO OPEN':
            summary.sell_to_open_amount += amount
            summary.open_position_quantity += quantity
            summary.fees += fees
        
        elif action == 'BUY TO OPEN':
            summary.buy_to_open_amount += amount
            summary.open_position_quantity += quantity
            summary.fees += fees
        
        elif action == 'BUY TO CLOSE':
            summary.buy_to_close_amount += amount
            summary.open_position_quantity -= quantity
            summary.fees += fees
        
        elif action == 'SELL TO CLOSE':
            summary.sell_to_close_amount += amount
            summary.open_position_quantity -= quantity
            summary.fees += fees
        
        elif action == 'EXPIRED':
            self._handle_expiration(transaction, option_info, summary)
        
        elif action == 'ASSIGNED':
            self._handle_assignment(transaction, option_info, summary)

        # 取引後の状態更新
        if summary.open_position_quantity == 0 and not summary.is_closed:
            summary.is_closed = True
            summary.close_date = transaction.transaction_date
            self._calculate_net_premium(transaction.symbol, summary)

        # プレミアムレコードの更新または作成
        if transaction.symbol not in self._premium_records:
            premium_amount = self._create_money_with_rate(Decimal('0'), exchange_rate)
            self._premium_records[transaction.symbol] = PremiumRecord(
                trade_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                expiry_date=option_info['expiry_date'],
                strike_price=option_info['strike_price'],
                option_type=option_info['option_type'],
                premium_amount=premium_amount,
                exchange_rate=exchange_rate,
                description=transaction.description
            )

    def _handle_expiration(self, transaction: Transaction, option_info: Dict, summary: OptionTransactionSummary) -> None:
        """期限切れの処理"""
        if not summary.is_closed:
            # 最終的なプレミアム計算
            self._calculate_net_premium(transaction.symbol, summary)
            summary.status = 'EXPIRED'
            summary.is_closed = True
            summary.close_date = transaction.transaction_date

    def _handle_assignment(self, transaction: Transaction, option_info: Dict, summary: OptionTransactionSummary) -> None:
        """権利行使の処理"""
        if not summary.is_closed:
            # 最終的なプレミアム計算
            self._calculate_net_premium(transaction.symbol, summary)
            
            # 権利行使情報を記録
            exercise_info = {
                'date': transaction.transaction_date,
                'quantity': abs(int(transaction.quantity or 0)),
                'strike_price': option_info['strike_price'],
                'net_premium': summary.net_premium,
                'net_premium_jpy': summary.net_premium_jpy  # 日本円でのプレミアムを追加
            }
            
            base_symbol = option_info['underlying']
            self._assignments[base_symbol].append(exercise_info)
            
            summary.status = 'ASSIGNED'
            summary.is_closed = True
            summary.close_date = transaction.transaction_date

    def _calculate_net_premium(self, symbol: str, summary: OptionTransactionSummary) -> None:
        """ネットプレミアムの計算（USD と JPY）"""
        # 取引による損益
        trading_gain = summary.sell_to_close_amount - summary.buy_to_close_amount
        
        # 最終的なプレミアム = オープン時の収支 + 取引損益 - 手数料
        premium = (summary.sell_to_open_amount - summary.buy_to_open_amount +
                  trading_gain - summary.fees)
        
        summary.net_premium = premium

        # 日本円でのプレミアム計算
        if summary.exchange_rate:
            summary.net_premium_jpy = premium * summary.exchange_rate

        if summary.is_closed and summary.status == 'OPEN':
            summary.status = 'CLOSED'

        # プレミアムレコードの更新
        if symbol in self._premium_records:
            premium_money = self._create_money_with_rate(premium, summary.exchange_rate)
            self._premium_records[symbol].premium_amount = premium_money
            if summary.exchange_rate:
                self._premium_records[symbol].premium_amount_jpy = premium_money.convert_to_jpy(summary.exchange_rate)

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

    def get_records(self) -> List[PremiumRecord]:
        """処理済みレコードを取得"""
        return list(self._premium_records.values())