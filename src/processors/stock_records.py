from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
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
    realized_gain: Money
    fees: Money
    
    # 為替情報
    exchange_rate: Decimal
    
    # 日本円換算額
    price_jpy: Optional[Money] = None
    realized_gain_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数量が整数で渡された場合の対応
        if isinstance(self.quantity, int):
            object.__setattr__(self, 'quantity', Decimal(str(self.quantity)))
        
        if not self.price_jpy:
            object.__setattr__(
                self, 
                'price_jpy', 
                self.price.convert(Currency.JPY)
            )
        
        if not self.realized_gain_jpy:
            object.__setattr__(
                self, 
                'realized_gain_jpy', 
                self.realized_gain.convert(Currency.JPY)
            )
        
        if not self.fees_jpy:
            object.__setattr__(
                self, 
                'fees_jpy', 
                self.fees.convert(Currency.JPY)
            )

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
    status: str = 'Open'
    initial_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    
    # 損益情報
    total_realized_gain: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0')))
    
    # 為替情報
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    
    # 日本円換算額
    total_realized_gain_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数量が整数で渡された場合の対応
        if isinstance(self.initial_quantity, int):
            object.__setattr__(self, 'initial_quantity', Decimal(str(self.initial_quantity)))
        
        if isinstance(self.remaining_quantity, int):
            object.__setattr__(self, 'remaining_quantity', Decimal(str(self.remaining_quantity)))
        
        # JPY変換
        if not self.total_realized_gain_jpy:
            object.__setattr__(
                self, 
                'total_realized_gain_jpy', 
                self.total_realized_gain.convert(Currency.JPY)
            )
        
        if not self.total_fees_jpy:
            object.__setattr__(
                self, 
                'total_fees_jpy', 
                self.total_fees.convert(Currency.JPY)
            )