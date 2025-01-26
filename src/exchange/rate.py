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

    def __mul__(self, other: Decimal) -> Decimal:
        """Decimalとの乗算をサポート"""
        if isinstance(other, Decimal):
            return self.convert(other)
        raise TypeError(f"サポートされていないオペランドタイプ: {type(other)}")

    def __rmul__(self, other: Decimal) -> Decimal:
        """右からの乗算をサポート"""
        return self.__mul__(other)

    def inverse(self) -> 'Rate':
        """逆レートを取得"""
        return Rate(
            base=self.target,
            target=self.base,
            value=Decimal('1') / self.value,
            date=self.date
        )

    def cross_rate(self, other: 'Rate') -> 'Rate':
        """クロスレートを計算"""
        if self.target != other.base:
            raise ValueError("クロスレート計算には通貨が一致する必要があります")
            
        return Rate(
            base=self.base,
            target=other.target,
            value=self.value * other.value,
            date=max(self.date, other.date)
        )

    def __str__(self) -> str:
        return f"{self.base.code}/{self.target.code}: {self.value:.4f}"