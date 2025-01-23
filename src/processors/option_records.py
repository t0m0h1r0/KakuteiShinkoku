from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class OptionTradeRecord:
    """オプション取引記録"""
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
    
    # オプション情報
    option_type: str     # 'Call' or 'Put'
    strike_price: Decimal
    expiry_date: date
    underlying: str
    
    # 損益情報
    trading_pnl: Money   # 反対売買による損益
    premium_pnl: Money   # プレミアム損益（期限切れ時）
    position_type: str   # 'Long' or 'Short'
    is_closed: bool      # 決済完了フラグ
    is_expired: bool     # 期限切れフラグ
    is_assigned: bool    # 権利行使フラグ
    
    # 日本円換算額
    price_jpy: Optional[Money] = None
    fees_jpy: Optional[Money] = None
    trading_pnl_jpy: Optional[Money] = None
    premium_pnl_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # quantityが整数で渡された場合の対応
        if isinstance(self.quantity, int):
            object.__setattr__(self, 'quantity', Decimal(str(self.quantity)))
            
        # strike_priceが数値型で渡された場合の対応
        if isinstance(self.strike_price, (int, float)):
            object.__setattr__(self, 'strike_price', Decimal(str(self.strike_price)))
        
        if not self.price_jpy:
            object.__setattr__(
                self, 
                'price_jpy', 
                self.price.convert(Currency.JPY)
            )
        
        if not self.fees_jpy:
            object.__setattr__(
                self, 
                'fees_jpy', 
                self.fees.convert(Currency.JPY)
            )
        
        if not self.trading_pnl_jpy:
            object.__setattr__(
                self, 
                'trading_pnl_jpy', 
                self.trading_pnl.convert(Currency.JPY)
            )
        
        if not self.premium_pnl_jpy:
            object.__setattr__(
                self, 
                'premium_pnl_jpy', 
                self.premium_pnl.convert(Currency.JPY)
            )

@dataclass
class OptionSummaryRecord:
    """オプション取引サマリー記録"""
    account_id: str
    symbol: str
    description: str
    underlying: str
    option_type: str
    strike_price: Decimal
    expiry_date: date
    
    # 取引情報
    open_date: date
    close_date: Optional[date] = None
    status: str = 'Open'
    initial_quantity: Decimal = Decimal('0')
    remaining_quantity: Decimal = Decimal('0')
    
    # 累計損益情報
    trading_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    premium_pnl: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_fees: Money = field(default_factory=lambda: Money(Decimal('0')))
    
    # 為替情報
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    
    # 日本円換算額
    trading_pnl_jpy: Optional[Money] = None
    premium_pnl_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数値型の変換
        if isinstance(self.initial_quantity, int):
            object.__setattr__(self, 'initial_quantity', Decimal(str(self.initial_quantity)))
        if isinstance(self.remaining_quantity, int):
            object.__setattr__(self, 'remaining_quantity', Decimal(str(self.remaining_quantity)))
        if isinstance(self.strike_price, (int, float)):
            object.__setattr__(self, 'strike_price', Decimal(str(self.strike_price)))
        
        # 損益のJPY変換
        if not self.trading_pnl_jpy:
            object.__setattr__(
                self, 
                'trading_pnl_jpy', 
                self.trading_pnl.convert(Currency.JPY)
            )
        
        if not self.premium_pnl_jpy:
            object.__setattr__(
                self, 
                'premium_pnl_jpy', 
                self.premium_pnl.convert(Currency.JPY)
            )
        
        if not self.total_fees_jpy:
            object.__setattr__(
                self, 
                'total_fees_jpy', 
                self.total_fees.convert(Currency.JPY)
            )