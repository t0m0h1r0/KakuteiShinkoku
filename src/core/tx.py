# core/tx.py

from dataclasses import dataclass
from decimal import Decimal
from datetime import date
from typing import Optional
from functools import total_ordering

from ..exchange.money import Money
from ..exchange.currency import Currency

@total_ordering
@dataclass(frozen=True)
class Transaction:
    """
    取引情報を表すイミュータブルなデータクラス
    
    Attributes:
        transaction_date (date): 取引日
        account_id (str): アカウントID
        symbol (str): 銘柄シンボル
        description (str): 取引説明
        amount (Decimal): 取引金額
        action_type (str): 取引種別
        quantity (Optional[Decimal]): 数量
        price (Optional[Decimal]): 価格
        fees (Optional[Decimal]): 手数料
    """
    transaction_date: date
    account_id: str
    symbol: str
    description: str
    amount: Decimal
    action_type: str
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fees: Optional[Decimal] = None

    def __post_init__(self) -> None:
        """
        データの整合性を確保するための初期化後処理
        """
        # 文字列フィールドの正規化
        object.__setattr__(self, 'account_id', self.account_id.strip())
        object.__setattr__(self, 'symbol', self.symbol.strip())
        object.__setattr__(self, 'description', self.description.strip())
        object.__setattr__(self, 'action_type', self.action_type.strip().upper())

        # Decimal型の正規化
        if isinstance(self.amount, (int, float)):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        if isinstance(self.quantity, (int, float)):
            object.__setattr__(self, 'quantity', Decimal(str(self.quantity)))
        if isinstance(self.price, (int, float)):
            object.__setattr__(self, 'price', Decimal(str(self.price)))
        if isinstance(self.fees, (int, float)):
            object.__setattr__(self, 'fees', Decimal(str(self.fees)))

    def create_money(self, currency: str = 'USD', rate_date: Optional[date] = None) -> Money:
        """
        トランザクション金額をMoneyオブジェクトに変換
        
        Args:
            currency (str): 通貨コード（デフォルト: 'USD'）
            rate_date (Optional[date]): 為替レート日付（デフォルト: 取引日）
            
        Returns:
            Money: 変換後のMoneyオブジェクト
        """
        return Money(
            amount=self.amount,
            currency=Currency.from_str(currency),
            rate_date=rate_date or self.transaction_date
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return (
            self.transaction_date == other.transaction_date and
            self.account_id == other.account_id and
            self.symbol == other.symbol and
            self.amount == other.amount
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Transaction):
            return NotImplemented
        return (
            self.transaction_date,
            self.account_id,
            self.symbol,
            self.amount
        ) < (
            other.transaction_date,
            other.account_id,
            other.symbol,
            other.amount
        )

    def __hash__(self) -> int:
        return hash((
            self.transaction_date,
            self.account_id,
            self.symbol,
            self.amount,
            self.action_type
        ))