from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

from ..core.money import Money

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
    price_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    realized_gain_jpy: Optional[Money] = None

    def __post_init__(self):
        """JPY金額の設定"""
        if self.exchange_rate and not self.price_jpy:
            self.price_jpy = self.price.convert_to_jpy(self.exchange_rate)
        if self.exchange_rate and not self.fees_jpy:
            self.fees_jpy = self.fees.convert_to_jpy(self.exchange_rate)
        if self.exchange_rate and not self.realized_gain_jpy:
            self.realized_gain_jpy = self.realized_gain.convert_to_jpy(self.exchange_rate)

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
    trading_gains: Money    # 譲渡損益
    premium_gains: Money    # プレミアム損益
    price_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    trading_gains_jpy: Optional[Money] = None
    premium_gains_jpy: Optional[Money] = None

    def __post_init__(self):
        """JPY金額の設定"""
        if self.exchange_rate:
            if not self.price_jpy:
                self.price_jpy = self.price.convert_to_jpy(self.exchange_rate)
            if not self.fees_jpy:
                self.fees_jpy = self.fees.convert_to_jpy(self.exchange_rate)
            if not self.trading_gains_jpy:
                self.trading_gains_jpy = self.trading_gains.convert_to_jpy(self.exchange_rate)
            if not self.premium_gains_jpy:
                self.premium_gains_jpy = self.premium_gains.convert_to_jpy(self.exchange_rate)

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
    description: str = ''
    premium_amount_jpy: Optional[Money] = None

    def __post_init__(self):
        """JPY金額の設定"""
        if self.exchange_rate and not self.premium_amount_jpy:
            self.premium_amount_jpy = self.premium_amount.convert_to_jpy(self.exchange_rate)