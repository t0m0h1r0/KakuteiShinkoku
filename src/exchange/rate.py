from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from .currency import Currency

@dataclass(frozen=True)
class Rate:
    """為替レートを表現するイミュータブルなクラス"""
    base: Currency
    target: Currency
    value: Decimal
    date: date
    
    def __post_init__(self):
        """パラメータの検証と変換"""
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))

        if self.base == self.target and self.value != Decimal('1'):
            raise ValueError("同一通貨間のレートは1でなければなりません")

    def convert(self, amount: Decimal) -> Decimal:
        """金額を変換"""
        converted = amount * self.value
        
        if self.target == Currency.JPY:
            return converted.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        return converted.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def inverse(self) -> 'Rate':
        """逆レートを取得"""
        return Rate(
            base=self.target,
            target=self.base,
            value=Decimal('1') / self.value,
            date=self.date
        )

    def __str__(self) -> str:
        return f"{self.base.code}/{self.target.code}: {self.value:.4f}"