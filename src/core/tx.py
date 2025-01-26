# core/tx.py

from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

from ..exchange.money import Money, Currency

@dataclass(frozen=True)
class Transaction:
    """取引情報を表すイミュータブルなデータクラス"""
    transaction_date: date
    account_id: str
    symbol: str
    description: str
    amount: Decimal
    action_type: str
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fees: Optional[Decimal] = None

    def create_money(self, currency: str = 'USD') -> Money:
        """トランザクション金額をMoneyオブジェクトに変換"""
        return Money(amount=self.amount, currency=currency)