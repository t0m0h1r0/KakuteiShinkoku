# exchange/rate.py

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from .currency import Currency


@dataclass(frozen=True)
class Rate:
    """為替レートを表現するイミュータブルなクラス"""

    base: Currency
    target: Currency
    value: Decimal
    rate_date: date
    source: str = "system"

    def __post_init__(self) -> None:
        """パラメータの検証と変換"""
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))

        self._validate_rate()

    def _validate_rate(self) -> None:
        """レートの検証"""
        if self.base == self.target and self.value != Decimal("1"):
            raise ValueError("同一通貨間のレートは1でなければなりません")

        if self.value <= Decimal("0"):
            raise ValueError(f"為替レートは正の値である必要があります: {self.value}")

    def convert(self, amount: Decimal, round_decimals: Optional[int] = None) -> Decimal:
        """金額を変換"""
        converted = amount * self.value

        if round_decimals is not None:
            return converted.quantize(
                Decimal(f"0.{'0' * round_decimals}"), rounding=ROUND_HALF_UP
            )

        # 通貨に応じた丸め処理
        if self.target == Currency.JPY:
            return converted.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return converted.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def inverse(self) -> "Rate":
        """逆レートを取得"""
        return Rate(
            base=self.target,
            target=self.base,
            value=Decimal("1") / self.value,
            rate_date=self.rate_date,
            source=f"inverse_{self.source}",
        )

    def with_date(self, new_date: date) -> "Rate":
        """日付を変更した新しいレートを取得"""
        return Rate(
            base=self.base,
            target=self.target,
            value=self.value,
            rate_date=new_date,
            source=self.source,
        )

    def format(self, decimals: int = 4) -> str:
        """レートのフォーマット"""
        rate_str = f"{self.value:.{decimals}f}"
        return f"{self.base.code}/{self.target.code}: {rate_str}"

    def __str__(self) -> str:
        return self.format()

    def __repr__(self) -> str:
        return (
            f"Rate(base={self.base.code}, target={self.target.code}, "
            f"value={self.value}, date={self.rate_date})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Rate):
            return NotImplemented
        return (
            self.base == other.base
            and self.target == other.target
            and self.value == other.value
            and self.rate_date == other.rate_date
        )

    def __hash__(self) -> int:
        return hash((self.base, self.target, self.value, self.rate_date))

    def __mul__(self, other: "Rate") -> "Rate":
        """レートの乗算（クロスレート計算）"""
        if self.target != other.base:
            raise ValueError(
                f"レートの連鎖が不正です: {self.target.code} != {other.base.code}"
            )

        return Rate(
            base=self.base,
            target=other.target,
            value=self.value * other.value,
            rate_date=max(self.rate_date, other.rate_date),
            source=f"cross_{self.source}_{other.source}",
        )
