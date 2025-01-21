from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..core.money import Money, Currency
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
            self.quantity = Decimal(str(self.quantity))
            
        # strike_priceが数値型で渡された場合の対応
        if isinstance(self.strike_price, (int, float)):
            self.strike_price = Decimal(str(self.strike_price))
            
        # 為替レートの設定
        if self.exchange_rate:
            if not self.price_jpy:
                self.price_jpy = self.price.convert_to_jpy(self.exchange_rate)
            if not self.fees_jpy:
                self.fees_jpy = self.fees.convert_to_jpy(self.exchange_rate)
            if not self.trading_pnl_jpy:
                self.trading_pnl_jpy = self.trading_pnl.convert_to_jpy(self.exchange_rate)
            if not self.premium_pnl_jpy:
                self.premium_pnl_jpy = self.premium_pnl.convert_to_jpy(self.exchange_rate)

@dataclass
class OptionSummaryRecord:
    """オプション取引サマリー記録"""
    # 基本情報
    account_id: str
    symbol: str
    description: str
    underlying: str
    option_type: str
    strike_price: Decimal
    expiry_date: date
    
    # 取引情報
    open_date: date
    close_date: Optional[date]
    status: str   # 'Open', 'Closed', 'Expired', 'Assigned'
    initial_quantity: Decimal
    remaining_quantity: Decimal
    
    # 累計損益情報
    trading_pnl: Money   # 反対売買による累計損益
    premium_pnl: Money   # プレミアムの累計損益
    total_fees: Money    # 累計手数料
    exchange_rate: Decimal
    
    # 日本円換算額
    trading_pnl_jpy: Optional[Money] = None
    premium_pnl_jpy: Optional[Money] = None
    total_fees_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 数値型の変換
        if isinstance(self.initial_quantity, int):
            self.initial_quantity = Decimal(str(self.initial_quantity))
        if isinstance(self.remaining_quantity, int):
            self.remaining_quantity = Decimal(str(self.remaining_quantity))
        if isinstance(self.strike_price, (int, float)):
            self.strike_price = Decimal(str(self.strike_price))
            
        # 為替レートの設定
        if self.exchange_rate:
            if not self.trading_pnl_jpy:
                self.trading_pnl_jpy = self.trading_pnl.convert_to_jpy(self.exchange_rate)
            if not self.premium_pnl_jpy:
                self.premium_pnl_jpy = self.premium_pnl.convert_to_jpy(self.exchange_rate)
            if not self.total_fees_jpy:
                self.total_fees_jpy = self.total_fees.convert_to_jpy(self.exchange_rate)