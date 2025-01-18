from dataclasses import dataclass
from decimal import Decimal
from datetime import date

from ..core.types.money import Money

@dataclass
class StockTradeRecord:
    """株式取引記録"""
    trade_date: date
    account_id: str
    symbol: str
    description: str
    action: str
    quantity: Decimal
    price: Money
    fees: Money
    realized_gain: Money
    exchange_rate: Decimal

@dataclass
class OptionTradeRecord:
    """オプション取引記録"""
    trade_date: date
    account_id: str
    symbol: str
    description: str
    action: str
    quantity: Decimal
    price: Money
    fees: Money
    expiry_date: str
    strike_price: Decimal
    option_type: str
    position_type: str
    is_expired: bool
    exchange_rate: Decimal

@dataclass
class PremiumRecord:
    """オプションプレミアム記録"""
    trade_date: date
    account_id: str
    symbol: str
    expiry_date: str
    strike_price: Decimal
    option_type: str
    premium_amount: Money
    exchange_rate: Decimal