import re
from decimal import Decimal
from typing import Optional, Dict, Any

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import OptionTradeRecord
from .stock_trade import StockTradeProcessor  # New import

class OptionTradeProcessor(BaseProcessor[OptionTradeRecord]):
    """オプション取引の処理クラス（権利行使連携対応）"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider, stock_processor: StockTradeProcessor):
        super().__init__(exchange_rate_provider)
        self.stock_processor = stock_processor
    
    def process(self, transaction: Transaction) -> None:
        """オプション取引トランザクションを処理"""
        if not self._is_option_trade(transaction):
            return
        
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        if transaction.action_type.upper() == 'ASSIGNED':
            # 権利行使情報を株式取引プロセッサに連携
            self._handle_assignment(transaction, option_info)
        
        trade_record = OptionTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            action=transaction.action_type,
            quantity=transaction.quantity or Decimal('0'),
            price=Money(transaction.price or Decimal('0')),
            fees=Money(transaction.fees or Decimal('0')),
            expiry_date=option_info['expiry_date'],
            strike_price=option_info['strike_price'],
            option_type=option_info['option_type'],
            position_type=self._determine_position_type(transaction.action_type, option_info['option_type']),
            is_expired=transaction.action_type.upper() == 'EXPIRED',
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
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