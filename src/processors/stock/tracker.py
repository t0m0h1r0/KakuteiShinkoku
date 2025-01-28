from decimal import Decimal
from typing import Dict
from datetime import date
from collections import defaultdict

from ..base.tracker import BaseTransactionTracker


class StockTransactionTracker(BaseTransactionTracker):
    """株式取引の状態を追跡するクラス"""

    def __init__(self):
        super().__init__()
        self._transaction_tracking = defaultdict(
            lambda: {
                "total_quantity": Decimal("0"),
                "total_cost": Decimal("0"),
                "total_realized_gain": Decimal("0"),
                "matured_dates": set(),
            }
        )

    def update_tracking(
        self,
        symbol: str,
        quantity: Decimal,
        cost: Decimal,
        realized_gain: Decimal = Decimal("0"),
    ) -> None:
        """取引状態を更新"""
        tracking = self._transaction_tracking[symbol]
        tracking["total_quantity"] += quantity
        tracking["total_cost"] += cost
        tracking["total_realized_gain"] += realized_gain

    def is_matured(self, symbol: str, date: date) -> bool:
        """満期状態のチェック"""
        return date in self._transaction_tracking[symbol]["matured_dates"]

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(
            symbol,
            {
                "total_quantity": Decimal("0"),
                "total_cost": Decimal("0"),
                "total_realized_gain": Decimal("0"),
                "matured_dates": set(),
            },
        )
