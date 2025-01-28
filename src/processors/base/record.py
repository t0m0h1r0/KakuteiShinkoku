from abc import ABC
from dataclasses import dataclass
from decimal import Decimal
from datetime import date


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
