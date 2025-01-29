from typing import Protocol, runtime_checkable, Optional, Union
from datetime import date
from decimal import Decimal


@runtime_checkable
class CurrencyProtocol(Protocol):
    """
    通貨に関するプロトコル
    
    通貨の基本的な情報と振る舞いを定義します。
    """
    @property
    def code(self) -> str: ...
    @property
    def symbol(self) -> str: ...
    @property
    def decimals(self) -> int: ...
    @property
    def display_name(self) -> str: ...
    @property
    def country(self) -> Optional[str]: ...

    def format_amount(
        self, amount: Union[Decimal, float, int], include_symbol: bool = True
    ) -> str: ...


@runtime_checkable
class RateProtocol(Protocol):
    """
    為替レートのプロトコル
    
    レートの変換と操作に関する基本的な振る舞いを定義します。
    """
    base: CurrencyProtocol
    target: CurrencyProtocol
    value: Decimal
    rate_date: date
    source: str

    def convert(
        self, amount: Decimal, round_decimals: Optional[int] = None
    ) -> Decimal: ...
    def inverse(self) -> "RateProtocol": ...
    def with_date(self, new_date: date) -> "RateProtocol": ...
    def format(self, decimals: int = 4) -> str: ...


@runtime_checkable
class MoneyProtocol(Protocol):
    """
    金額のプロトコル
    
    通貨金額の計算と変換に関する基本的な振る舞いを定義します。
    """
    currency: CurrencyProtocol
    rate_date: date

    def as_currency(self, target_currency: CurrencyProtocol) -> Decimal: ...
    def get_rate(self) -> Optional[float]: ...

    @property
    def usd(self) -> Decimal: ...

    @property
    def jpy(self) -> Decimal: ...

    def __add__(self, other: "MoneyProtocol") -> "MoneyProtocol": ...
    def __sub__(self, other: "MoneyProtocol") -> "MoneyProtocol": ...

    @classmethod
    def sum(cls, monies: list["MoneyProtocol"]) -> "MoneyProtocol": ...