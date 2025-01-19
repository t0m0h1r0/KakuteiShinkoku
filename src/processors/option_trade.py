import re
from decimal import Decimal
from typing import Optional, Dict

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import OptionTradeRecord

class OptionTradeProcessor(BaseProcessor[OptionTradeRecord]):
    """オプション取引の処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
    
    def process(self, transaction: Transaction) -> None:
        """オプション取引トランザクションを処理"""
        if not self._is_option_trade(transaction):
            return
            
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return
            
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
            position_type='Short' if 'SELL' in transaction.action_type.upper() else 'Long',
            is_expired=transaction.action_type.upper() == 'EXPIRED',
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
        
        self.records.append(trade_record)
    
    def _is_option_trade(self, transaction: Transaction) -> bool:
        """オプション取引トランザクションかどうかを判定"""
        option_actions = {'BUY', 'SELL', 'EXPIRED', 'ASSIGNED'}
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
            parts = symbol.split()
            return {
                'base_symbol': parts[0],
                'expiry_date': parts[1],
                'strike_price': Decimal(parts[2]),
                'option_type': parts[3]
            }
        except (IndexError, ValueError):
            return None