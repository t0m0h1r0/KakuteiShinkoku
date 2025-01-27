# core/tx.py

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any
from enum import Enum, auto

from ..exchange.money import Money, Currency

class TransactionType(Enum):
    """取引種別を表す列挙型"""
    BUY = auto()
    SELL = auto()
    DIVIDEND = auto()
    INTEREST = auto()
    TAX = auto()
    FEE = auto()
    JOURNAL = auto()
    OTHER = auto()

    @classmethod
    def from_str(cls, action: str) -> 'TransactionType':
        """文字列から取引種別を判定"""
        action_upper = action.upper()
        
        if 'BUY' in action_upper:
            return cls.BUY
        elif 'SELL' in action_upper:
            return cls.SELL
        elif 'DIVIDEND' in action_upper:
            return cls.DIVIDEND
        elif 'INTEREST' in action_upper:
            return cls.INTEREST
        elif 'TAX' in action_upper:
            return cls.TAX
        elif 'FEE' in action_upper or 'COMMISSION' in action_upper:
            return cls.FEE
        elif 'JOURNAL' in action_upper:
            return cls.JOURNAL
        return cls.OTHER

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
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初期化後の処理"""
        # frozenクラスでもmetadataは変更可能にする
        object.__setattr__(self, 'metadata', dict(self.metadata))

    @property
    def transaction_type(self) -> TransactionType:
        """取引種別を判定"""
        return TransactionType.from_str(self.action_type)

    @property
    def is_buy(self) -> bool:
        """買い取引かどうか"""
        return self.transaction_type == TransactionType.BUY

    @property
    def is_sell(self) -> bool:
        """売り取引かどうか"""
        return self.transaction_type == TransactionType.SELL

    @property
    def is_dividend(self) -> bool:
        """配当取引かどうか"""
        return self.transaction_type == TransactionType.DIVIDEND

    @property
    def is_interest(self) -> bool:
        """利子取引かどうか"""
        return self.transaction_type == TransactionType.INTEREST

    @property
    def total_amount(self) -> Decimal:
        """手数料を含む総額を計算"""
        base = abs(self.amount)
        if self.fees:
            base += abs(self.fees)
        return base

    def create_money(self, currency: Currency = Currency.USD, rate_date: Optional[date] = None) -> Money:
        """トランザクション金額をMoneyオブジェクトに変換"""
        use_date = rate_date or self.transaction_date
        return Money(amount=self.amount, currency=currency, rate_date=use_date)

    def with_metadata(self, **kwargs) -> 'Transaction':
        """メタデータを追加した新しいトランザクションを作成"""
        new_metadata = dict(self.metadata)
        new_metadata.update(kwargs)
        return Transaction(
            transaction_date=self.transaction_date,
            account_id=self.account_id,
            symbol=self.symbol,
            description=self.description,
            amount=self.amount,
            action_type=self.action_type,
            quantity=self.quantity,
            price=self.price,
            fees=self.fees,
            metadata=new_metadata
        )