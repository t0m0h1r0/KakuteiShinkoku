from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

from ...exchange.money import Money
from ...exchange.currency import Currency


@dataclass
class StockTradeRecord:
    trade_date: date
    account_id: str
    symbol: str
    description: str
    action: str
    quantity: Decimal
    price: Money
    realized_gain: Money
    fees: Money
    exchange_rate: Decimal

    @property
    def price_jpy(self):
        return self.price.convert(Currency.JPY)

    @property
    def realized_gain_jpy(self):
        return self.realized_gain.convert(Currency.JPY)

    @property
    def fees_jpy(self):
        return self.fees.convert(Currency.JPY)


@dataclass
class StockSummaryRecord:
    account_id: str
    symbol: str
    description: str
    open_date: date
    initial_quantity: Decimal
    close_date: Optional[date] = None
    remaining_quantity: Decimal = Decimal("0")
    total_realized_gain: Money = Money(Decimal("0"), Currency.USD)
    total_fees: Money = Money(Decimal("0"), Currency.USD)
