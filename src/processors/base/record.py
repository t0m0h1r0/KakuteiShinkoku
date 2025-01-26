from abc import ABC
from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

from ...exchange.money import Money
from ...exchange.currency import Currency

@dataclass
class BaseTradeRecord(ABC):
    """基本取引記録"""
    record_date: date
    account_id: str
    symbol: str
    description: str
    exchange_rate: Decimal

@dataclass
class BaseSummaryRecord(ABC):
    """基本サマリー記録"""
    account_id: str
    symbol: str
    description: str
    open_date: date
    close_date: Optional[date] = None
    remaining_quantity: Decimal = Decimal('0')
    status: str = 'Open'

    @property
    def is_closed(self) -> bool:
        return self.close_date is not None or self.status == 'Closed'