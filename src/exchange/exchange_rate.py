from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .currency import Currency

@dataclass(frozen=True)
class ExchangeRate:
    """特定日付の為替レートを表現するクラス"""
    base_currency: Currency
    target_currency: Currency
    rate: Decimal
    date: date
    
    def __post_init__(self):
        """パラメータのバリデーションと型変換"""
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, 'rate', Decimal(str(self.rate)))
    
    def convert(self, amount: Decimal) -> Decimal:
        """指定された金額を通貨変換"""
        converted = amount * self.rate
        # 通貨に応じて丸め処理を変更
        if self.target_currency == Currency.JPY:
            return converted.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)