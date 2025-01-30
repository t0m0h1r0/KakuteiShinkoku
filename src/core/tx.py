from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any, ClassVar, Final
from enum import Enum, auto
from abc import ABC, abstractmethod

from ..exchange.money import Money
from ..exchange.currency import Currency


class TransactionType(Enum):
    """
    取引種別を表す列挙型

    全ての取引タイプを定義し、文字列からの変換をサポートします。
    """

    BUY = auto()  # 買付
    SELL = auto()  # 売却
    DIVIDEND = auto()  # 配当
    INTEREST = auto()  # 利子
    TAX = auto()  # 税金
    FEE = auto()  # 手数料
    JOURNAL = auto()  # 振替
    OTHER = auto()  # その他

    @classmethod
    def from_str(cls, action: str) -> TransactionType:
        """
        文字列から取引種別を判定

        Args:
            action: 判定する取引アクション文字列

        Returns:
            TransactionType: 対応する取引種別

        Examples:
            >>> TransactionType.from_str("BUY")
            TransactionType.BUY
            >>> TransactionType.from_str("Dividend Payment")
            TransactionType.DIVIDEND
        """
        action_upper = action.upper()

        # 取引種別の判定マッピング
        TYPE_MAPPING: Final[Dict[str, TransactionType]] = {
            "BUY": cls.BUY,
            "SELL": cls.SELL,
            "DIVIDEND": cls.DIVIDEND,
            "INTEREST": cls.INTEREST,
            "TAX": cls.TAX,
            "FEE": cls.FEE,
            "COMMISSION": cls.FEE,
            "JOURNAL": cls.JOURNAL,
        }

        # 完全一致で判定
        if action_upper in TYPE_MAPPING:
            return TYPE_MAPPING[action_upper]

        # 部分一致で判定
        for key, value in TYPE_MAPPING.items():
            if key in action_upper:
                return value

        return cls.OTHER


class TransactionValidator(ABC):
    """
    トランザクションバリデーションの抽象基底クラス
    """

    @abstractmethod
    def validate(self, transaction: Transaction) -> bool:
        """
        トランザクションを検証

        Args:
            transaction: 検証対象のトランザクション

        Returns:
            bool: 検証結果
        """
        pass


class BasicTransactionValidator(TransactionValidator):
    """
    基本的なトランザクション検証を行うクラス
    """

    def validate(self, transaction: Transaction) -> bool:
        """
        基本的な検証を実行

        Args:
            transaction: 検証対象のトランザクション

        Returns:
            bool: 検証結果
        """
        if not transaction.transaction_date:
            return False

        if not transaction.account_id:
            return False

        if transaction.amount is None:
            return False

        return True


@dataclass(frozen=True)
class Transaction:
    """
    取引情報を表すイミュータブルなデータクラス

    全ての取引に関する基本情報を保持し、計算や変換のメソッドを提供します。
    frozenなデータクラスとして実装され、作成後の変更を防止します。
    """

    # クラス変数
    ROUND_DIGITS: ClassVar[int] = 2
    DEFAULT_CURRENCY: ClassVar[Currency] = Currency.USD

    # 基本情報
    transaction_date: date
    account_id: str
    symbol: str
    description: str
    amount: Decimal
    action_type: str

    # オプション情報
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fees: Optional[Decimal] = None

    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)
    _validator: TransactionValidator = field(
        default_factory=BasicTransactionValidator, init=False
    )

    def __post_init__(self) -> None:
        """
        初期化後の処理

        バリデーションを実行し、必要な型変換を行います。
        """
        # メタデータは後から更新可能に
        object.__setattr__(self, "metadata", dict(self.metadata))

        # バリデーション
        if not self._validator.validate(self):
            raise ValueError("トランザクションの検証に失敗しました")

        # Decimal型への変換
        self._convert_to_decimal()

    def _convert_to_decimal(self) -> None:
        """数値フィールドをDecimal型に変換"""
        fields_to_convert = ["amount", "quantity", "price", "fees"]
        for field in fields_to_convert:
            value = getattr(self, field, None)
            if value is not None and not isinstance(value, Decimal):
                object.__setattr__(self, field, Decimal(str(value)))

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
        """
        手数料を含む総額を計算

        Returns:
            Decimal: 総額（手数料込み）
        """
        base = abs(self.amount)
        if self.fees:
            base += abs(self.fees)
        return base.quantize(Decimal(f"0.{('0' * self.ROUND_DIGITS)}"))

    def create_money(
        self, currency: Currency = DEFAULT_CURRENCY, rate_date: Optional[date] = None
    ) -> Money:
        """
        トランザクション金額をMoneyオブジェクトに変換

        Args:
            currency: 通貨（デフォルト: USD）
            rate_date: レート参照日（デフォルト: 取引日）

        Returns:
            Money: 作成されたMoneyオブジェクト
        """
        use_date = rate_date or self.transaction_date
        return Money(amount=self.amount, currency=currency, rate_date=use_date)

    def with_metadata(self, **kwargs) -> Transaction:
        """
        メタデータを追加した新しいトランザクションを作成

        Args:
            **kwargs: 追加するメタデータのキーワード引数

        Returns:
            Transaction: 新しいTransactionインスタンス

        Examples:
            >>> tx = Transaction(...)
            >>> new_tx = tx.with_metadata(processed=True, batch_id="123")
        """
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
            metadata=new_metadata,
        )

    def __str__(self) -> str:
        """文字列表現を返す"""
        return (
            f"Transaction({self.transaction_date}, {self.action_type}, "
            f"{self.symbol}, {self.amount})"
        )

    def __repr__(self) -> str:
        """開発者向けの詳細な文字列表現を返す"""
        return (
            f"Transaction(date={self.transaction_date}, "
            f"action={self.action_type}, symbol={self.symbol}, "
            f"amount={self.amount}, quantity={self.quantity}, "
            f"price={self.price}, fees={self.fees})"
        )