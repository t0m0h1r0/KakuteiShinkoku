from dataclasses import dataclass, field
from decimal import Decimal

from ...exchange.money import Money
from ...exchange.currency import Currency
from ..base.record import BaseSummaryRecord, BaseTradeRecord


@dataclass
class InterestTradeRecord(BaseTradeRecord):
    """利子取引記録"""

    action_type: str
    income_type: str

    gross_amount: Money
    tax_amount: Money

    @property
    def gross_amount_jpy(self) -> Money:
        return self.gross_amount.as_currency(Currency.JPY)

    @property
    def tax_amount_jpy(self) -> Money:
        return self.tax_amount.as_currency(Currency.JPY)

    @property
    def net_amount(self) -> Money:
        return self.gross_amount - self.tax_amount

    @property
    def net_amount_jpy(self) -> Money:
        return self.net_amount.as_currency(Currency.JPY)


@dataclass
class InterestSummaryRecord(BaseSummaryRecord):
    total_gross_amount: Money = field(
        default_factory=lambda: Money(Decimal("0"), Currency.USD)
    )
    total_tax_amount: Money = field(
        default_factory=lambda: Money(Decimal("0"), Currency.USD)
    )

    @property
    def total_net_amount(self) -> Money:
        return self.total_gross_amount - self.total_tax_amount

    @property
    def total_gross_amount_jpy(self) -> Money:
        return self.total_gross_amount.as_currency(Currency.JPY)

    @property
    def total_tax_amount_jpy(self) -> Money:
        return self.total_tax_amount.as_currency(Currency.JPY)

    @property
    def total_net_amount_jpy(self) -> Money:
        return self.total_net_amount.as_currency(Currency.JPY)
