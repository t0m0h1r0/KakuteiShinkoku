from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class InterestTradeRecord:
    """利子取引記録"""
    # 基本情報
    record_date: date
    account_id: str
    symbol: str
    description: str
    income_type: str
    action_type: str
    is_matured: bool
    
    # 金額情報
    gross_amount: Money
    tax_amount: Money
    
    # 為替情報
    exchange_rate: Decimal
    
    # 日本円換算額
    gross_amount_jpy: Optional[Money] = None
    tax_amount_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 為替レートが提供されている場合、JPY金額を計算
        if not self.gross_amount_jpy:
            object.__setattr__(
                self, 
                'gross_amount_jpy', 
                self.gross_amount.convert(Currency.JPY)
            )
        
        if not self.tax_amount_jpy:
            object.__setattr__(
                self, 
                'tax_amount_jpy', 
                self.tax_amount.convert(Currency.JPY)
            )

@dataclass
class InterestSummaryRecord:
    """利子サマリー記録"""
    account_id: str
    symbol: str
    description: str
    
    # 集計情報
    total_gross_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    total_tax_amount: Money = field(default_factory=lambda: Money(Decimal('0')))
    
    # 為替情報
    exchange_rate: Decimal = DEFAULT_EXCHANGE_RATE
    
    # 日本円換算額
    total_gross_amount_jpy: Optional[Money] = None
    total_tax_amount_jpy: Optional[Money] = None
    
    def __post_init__(self):
        """JPY金額の設定"""
        # 総額のJPY変換
        if not self.total_gross_amount_jpy:
            object.__setattr__(
                self, 
                'total_gross_amount_jpy', 
                self.total_gross_amount.convert(Currency.JPY)
            )
        
        if not self.total_tax_amount_jpy:
            object.__setattr__(
                self, 
                'total_tax_amount_jpy', 
                self.total_tax_amount.convert(Currency.JPY)
            )