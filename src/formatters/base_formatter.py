from abc import ABC, abstractmethod
from typing import Any, Dict
from decimal import Decimal
from ..core.money import Money

class BaseFormatter(ABC):
    """表示フォーマットの基底クラス"""
    
    @abstractmethod
    def format(self, data: Any) -> str:
        """データをフォーマット"""
        pass

    def _format_money(self, amount: Money, decimal_places: int = 2) -> str:
        """金額のフォーマット"""
        if isinstance(amount, Money):
            return f"{amount.amount:.{decimal_places}f}"
        elif isinstance(amount, (Decimal, float)):
            return f"{amount:.{decimal_places}f}"
        return str(amount)

    def _format_currency(self, amount: Money, currency_symbol: str = '$') -> str:
        """通貨付き金額のフォーマット"""
        return f"{currency_symbol}{self._format_money(amount)}"