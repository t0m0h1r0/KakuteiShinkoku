from decimal import Decimal
from typing import Dict
from collections import defaultdict

from ..base.tracker import BaseTransactionTracker


class DividendTransactionTracker(BaseTransactionTracker):
    def __init__(self):
        super().__init__()
        self._transaction_tracking = defaultdict(
            lambda: {"total_amount": Decimal("0"), "total_tax": Decimal("0")}
        )

    def update_tracking(
        self, symbol: str, amount: Decimal, tax: Decimal = Decimal("0")
    ) -> None:
        tracking = self._transaction_tracking[symbol]
        tracking["total_amount"] += amount
        tracking["total_tax"] += tax

    def get_tracking_info(self, symbol: str) -> Dict:
        return self._transaction_tracking.get(
            symbol, {"total_amount": Decimal("0"), "total_tax": Decimal("0")}
        )
