# src/models/data_models.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Transaction:
    date: str
    account: str
    symbol: str
    description: str
    amount: Decimal
    action: str

@dataclass(frozen=True)
class DividendRecord:
    date: str
    account: str
    symbol: str
    description: str
    type: str
    gross_amount: Decimal
    tax: Decimal
    exchange_rate: Decimal
    reinvested: bool

    @property
    def net_amount_usd(self) -> Decimal:
        return round(self.gross_amount - self.tax, 2)

    @property
    def net_amount_jpy(self) -> Decimal:
        return round((self.gross_amount - self.tax) * self.exchange_rate)
