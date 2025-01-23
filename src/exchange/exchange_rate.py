from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .currency import Currency

@dataclass(frozen=True)
class ExchangeRate:
    """為替レートを表現するイミュータブルなクラス"""
    base_currency: Currency
    target_currency: Currency
    rate: Decimal
    date: date
    
    def __post_init__(self):
        """パラメータの検証と変換"""
        if not isinstance(self.rate, Decimal):
            object.__setattr__(self, 'rate', Decimal(str(self.rate)))

        if self.base_currency == self.target_currency and self.rate != Decimal('1'):
            raise ValueError("同一通貨間のレートは1でなければなりません")

    def convert(self, amount: Decimal) -> Decimal:
        """金額を変換"""
        converted = amount * self.rate
        
        # 通貨に応じて丸め処理
        if self.target_currency == Currency.JPY:
            return converted.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def inverse(self) -> 'ExchangeRate':
        """逆レートを取得"""
        return ExchangeRate(
            base_currency=self.target_currency,
            target_currency=self.base_currency,
            rate=Decimal('1') / self.rate,
            date=self.date
        )

    def cross_rate(self, other: 'ExchangeRate') -> 'ExchangeRate':
        """クロスレートを計算"""
        if self.target_currency != other.base_currency:
            raise ValueError("クロスレート計算には通貨が一致する必要があります")
            
        return ExchangeRate(
            base_currency=self.base_currency,
            target_currency=other.target_currency,
            rate=self.rate * other.rate,
            date=max(self.date, other.date)
        )

    def __str__(self) -> str:
        return f"{self.base_currency}/{self.target_currency}: {self.rate:.4f}"