from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money
from ..exchange.currency import Currency
from ..exchange.rate_provider import RateProvider
from ..config.settings import DEFAULT_EXCHANGE_RATE

@dataclass
class DividendTradeRecord:
    """配当取引記録"""
    # 基本情報
    record_date: date
    account_id: str
    symbol: str
    description: str
    action_type: str    # 追加：アクションタイプ
    income_type: str
    
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
        rate_provider = RateProvider()
        
        if not self.gross_amount_jpy:
            object.__setattr__(
                self, 
                'gross_amount_jpy', 
                self.gross_amount.convert(
                    Currency.JPY, 
                    rate_provider
                )
            )
        
        if not self.tax_amount_jpy:
            object.__setattr__(
                self, 
                'tax_amount_jpy', 
                self.tax_amount.convert(
                    Currency.JPY, 
                    rate_provider
                )
            )

@dataclass
class DividendSummaryRecord:
    """配当サマリー記録"""
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
        # 為替レートが提供されている場合、JPY金額を計算
        rate_provider = RateProvider()
        
        if not self.total_gross_amount_jpy:
            object.__setattr__(
                self, 
                'total_gross_amount_jpy', 
                self.total_gross_amount.convert(
                    Currency.JPY, 
                    rate_provider
                )
            )
        
        if not self.total_tax_amount_jpy:
            object.__setattr__(
                self, 
                'total_tax_amount_jpy', 
                self.total_tax_amount.convert(
                    Currency.JPY, 
                    rate_provider
                )
            )