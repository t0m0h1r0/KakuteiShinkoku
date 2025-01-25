from decimal import Decimal
from typing import Dict, List
from datetime import date
from collections import defaultdict

from ..base.tracker import BaseTransactionTracker
from ...core.transaction import Transaction

class InterestTransactionTracker(BaseTransactionTracker):
    """利子取引の状態を追跡するクラス"""
    def __init__(self):
        super().__init__()
        self._transaction_tracking = defaultdict(lambda: {
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0')
        })

    def update_tracking(self, symbol: str, amount: Decimal, tax: Decimal = Decimal('0')) -> None:
        """取引状態を更新"""
        tracking = self._transaction_tracking[symbol]
        tracking['total_amount'] += amount
        tracking['total_tax'] += tax

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(symbol, {
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0')
        })