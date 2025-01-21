from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..core.money import Money, Currency
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class StockTradeRecord:
    """株式取引記録"""
    # 基本情報
    trade_date: date
    account_id: str
    symbol: str
    description: str
    
    # 取引情報
    action: str
    quantity: Decimal
    price: Money
    fees: Money
    exchange_rate: Decimal
    
    # 損益情報
    realized_gain: Money
    
    # 日本円換算額
    price_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    realized_gain_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数量が整数で渡された場合の対応
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
            
        # 為替レートの設定
        if self.exchange_rate:
            if not self.price_jpy:
                self.price_jpy = self.price.convert_to_jpy(self.exchange_rate)
            if not self.fees_jpy:
                self.fees_jpy = self.fees.convert_to_jpy(self.exchange_rate)
            if not self.realized_gain_jpy:
                self.realized_gain_jpy = self.realized_gain.convert_to_jpy(self.exchange_rate)

@dataclass
class StockSummaryRecord:
    """株式取引サマリー記録"""
    # 基本情報
    account_id: str
    symbol: str
    description: str
    
    # 取引情報
    open_date: date
    close_date: Optional[date] = None
    status: str = 'Open'  # 'Open' or 'Closed'
    initial_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    
    # 損益情報
    total_realized_gain: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0'), Currency.USD))
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    
    # 日本円換算額
    total_realized_gain_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数量が整数で渡された場合の対応
        if isinstance(self.initial_quantity, int):
            self.initial_quantity = Decimal(str(self.initial_quantity))
        if isinstance(self.remaining_quantity, int):
            self.remaining_quantity = Decimal(str(self.remaining_quantity))

        # 為替レートの設定
        if self.exchange_rate:
            if not self.total_realized_gain_jpy:
                self.total_realized_gain_jpy = self.total_realized_gain.convert_to_jpy(self.exchange_rate)
            if not self.total_fees_jpy:
                self.total_fees_jpy = self.total_fees.convert_to_jpy(self.exchange_rate)