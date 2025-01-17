from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional

@dataclass(frozen=True)
class Money:
    """金額を表すイミュータブルなデータクラス"""
    amount: Decimal
    currency: str = 'USD'

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

@dataclass(frozen=True)
class DividendRecord:
    """配当収入記録を表すイミュータブルなデータクラス"""
    record_date: date
    account_id: str
    symbol: str
    description: str
    income_type: str
    gross_amount: Money
    tax_amount: Money
    exchange_rate: Decimal
    is_reinvested: bool
    principal_amount: Money = Money(Decimal('0'), 'USD')

    @property
    def gross_amount_jpy(self) -> Money:
        """日本円での総額"""
        return Money(
            self.gross_amount.amount * self.exchange_rate,
            'JPY'
        )

    @property
    def tax_jpy(self) -> Money:
        """日本円での税額"""
        return Money(
            self.tax_amount.amount * self.exchange_rate,
            'JPY'
        )

    @property
    def net_amount_usd(self) -> Money:
        """米ドルでの手取り額"""
        return Money(self.gross_amount.amount - self.tax_amount.amount)

    @property
    def net_amount_jpy(self) -> Money:
        """日本円での手取り額"""
        return Money(
            (self.gross_amount.amount - self.tax_amount.amount) * self.exchange_rate,
            'JPY'
        )

@dataclass(frozen=True)
class Position:
    """ポジション情報を表すイミュータブルなデータクラス"""
    symbol: str
    quantity: Decimal
    cost_basis: Money
    
    @property
    def average_cost(self) -> Money:
        """平均取得単価"""
        if self.quantity == 0:
            return Money(Decimal('0'))
        return Money(self.cost_basis.amount / self.quantity)

@dataclass(frozen=True)
class TradeRecord:
    """取引記録を表すイミュータブルなデータクラス"""
    trade_date: date
    account_id: str
    symbol: str
    description: str
    trade_type: str
    action: str
    quantity: Decimal
    price: Money
    fees: Money
    realized_gain: Money
    cost_basis: Money
    proceeds: Money
    exchange_rate: Decimal
    holding_period_days: Optional[int] = None

    @property
    def cost_basis_jpy(self) -> Money:
        """日本円での取得価額"""
        return Money(
            self.cost_basis.amount * self.exchange_rate,
            'JPY'
        )

    @property
    def proceeds_jpy(self) -> Money:
        """日本円での売却額"""
        return Money(
            self.proceeds.amount * self.exchange_rate,
            'JPY'
        )

    @property
    def realized_gain_jpy(self) -> Money:
        """日本円での実現損益"""
        return Money(
            self.realized_gain.amount * self.exchange_rate,
            'JPY'
        )

    @property
    def fees_jpy(self) -> Money:
        """日本円での手数料"""
        return Money(
            self.fees.amount * self.exchange_rate,
            'JPY'
        )