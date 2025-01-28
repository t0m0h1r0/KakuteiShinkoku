from decimal import Decimal
from typing import Dict, List
from collections import defaultdict

from ..base.tracker import BaseTransactionTracker
from ...core.tx import Transaction
from ..option.config import OptionProcessingConfig


class OptionTransactionTracker(BaseTransactionTracker):
    """オプション取引の状態を追跡するクラス"""

    def __init__(self):
        super().__init__()
        self._transaction_tracking = defaultdict(
            lambda: {
                "open_quantity": Decimal("0"),
                "close_quantity": Decimal("0"),
                "trading_pnl": Decimal("0"),
                "premium_pnl": Decimal("0"),
                "fees": Decimal("0"),
                "max_status": "Open",
            }
        )
        self._daily_transactions = defaultdict(lambda: defaultdict(list))
        self._option_info = defaultdict(dict)

    def track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """日次トランザクションを追跡"""
        for transaction in transactions:
            symbol = transaction.symbol
            self._daily_transactions[symbol][transaction.transaction_date].append(
                transaction
            )

    def update_tracking(
        self,
        symbol: str,
        action: str,
        quantity: Decimal,
        pnl: Dict[str, Decimal] = None,
    ) -> None:
        """取引状態を更新"""
        tracking = self._transaction_tracking[symbol]

        if action in OptionProcessingConfig.ACTION_TYPES["OPEN"]:
            tracking["open_quantity"] += quantity
        elif action in OptionProcessingConfig.ACTION_TYPES["CLOSE"]:
            tracking["close_quantity"] += quantity

        if pnl:
            tracking["trading_pnl"] = tracking.get("trading_pnl", 0) + pnl.get(
                "trading_pnl", 0
            )
            tracking["premium_pnl"] = tracking.get("premium_pnl", 0) + pnl.get(
                "premium_pnl", 0
            )
            if "fees" in pnl:
                tracking["fees"] = tracking.get("fees", 0) + pnl["fees"]

        self._update_status(tracking)

    def _update_status(self, tracking: Dict) -> None:
        """取引状態の更新"""
        if tracking["open_quantity"] > 0:
            if tracking["close_quantity"] >= tracking["open_quantity"]:
                tracking["max_status"] = "Closed"
            else:
                tracking["max_status"] = "Open"

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(
            symbol,
            {
                "open_quantity": Decimal("0"),
                "close_quantity": Decimal("0"),
                "trading_pnl": Decimal("0"),
                "premium_pnl": Decimal("0"),
                "fees": Decimal("0"),
                "max_status": "Open",
            },
        )
