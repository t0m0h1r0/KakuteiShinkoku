from typing import Dict, List
from datetime import date
import logging

from ...core.transaction import Transaction

class BaseTransactionTracker:
    """基本トランザクション追跡クラス"""
    def __init__(self):
        self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = {}
        self._transaction_tracking: Dict[str, Dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """日次トランザクションを追跡"""
        for transaction in transactions:
            symbol = transaction.symbol or 'GENERAL'
            if symbol not in self._daily_transactions:
                self._daily_transactions[symbol] = {}
            
            date = transaction.transaction_date
            if date not in self._daily_transactions[symbol]:
                self._daily_transactions[symbol][date] = []
            
            self._daily_transactions[symbol][date].append(transaction)

    def get_symbol_transactions(self, symbol: str) -> Dict[date, List[Transaction]]:
        """特定のシンボルの全トランザクションを取得"""
        return self._daily_transactions.get(symbol, {})

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(symbol, {})