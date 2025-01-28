from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional, Dict, Any
from enum import Enum, auto

from ..exchange.money import Money, Currency

class TransactionType(Enum):
    """
    取引種別を表す列挙型
    
    全ての取引タイプを定義し、文字列からの変換をサポートします。
    """
    BUY = auto()          # 買付
    SELL = auto()         # 売却
    DIVIDEND = auto()     # 配当
    INTEREST = auto()     # 利子
    TAX = auto()          # 税金
    FEE = auto()          # 手数料
    JOURNAL = auto()      # 振替
    OTHER = auto()        # その他

    @classmethod
    def from_str(cls, action: str) -> 'TransactionType':
        """
        文字列から取引種別を判定
        
        Args:
            action: 判定する取引アクション文字列
            
        Returns:
            対応するTransactionType
        """
        action_upper = action.upper()
        
        # 取引種別の判定マッピング
        type_mapping = {
            'BUY': cls.BUY,
            'SELL': cls.SELL,
            'DIVIDEND': cls.DIVIDEND,
            'INTEREST': cls.INTEREST,
            'TAX': cls.TAX,
            'FEE': cls.FEE,
            'COMMISSION': cls.FEE,
            'JOURNAL': cls.JOURNAL
        }
        
        # 部分一致で判定
        for key, value in type_mapping.items():
            if key in action_upper:
                return value
                
        return cls.OTHER

@dataclass(frozen=True)
class Transaction:
    """
    取引情報を表すイミュータブルなデータクラス
    
    全ての取引に関する基本情報を保持し、計算や変換のメソッドを提供します。
    frozenなデータクラスとして実装され、作成後の変更を防止します。
    """
    # 基本情報
    transaction_date: date     # 取引日
    account_id: str           # アカウントID
    symbol: str               # 銘柄シンボル
    description: str          # 取引説明
    amount: Decimal          # 取引金額
    action_type: str         # 取引アクション
    
    # オプション情報
    quantity: Optional[Decimal] = None      # 数量
    price: Optional[Decimal] = None         # 価格
    fees: Optional[Decimal] = None          # 手数料
    
    # メタデータ
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """
        初期化後の処理
        
        metadataは後から更新可能にするため、frozenクラスでも
        変更可能な新しい辞書を割り当てます。
        """
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
        """
        手数料を含む総額を計算
        
        Returns:
            総額（手数料込み）
        """
        base = abs(self.amount)
        if self.fees:
            base += abs(self.fees)
        return base

    def create_money(
        self, 
        currency: Currency = Currency.USD,
        rate_date: Optional[date] = None
    ) -> Money:
        """
        トランザクション金額をMoneyオブジェクトに変換
        
        Args:
            currency: 通貨（デフォルト: USD）
            rate_date: レート参照日（デフォルト: 取引日）
            
        Returns:
            作成されたMoneyオブジェクト
        """
        use_date = rate_date or self.transaction_date
        return Money(
            amount=self.amount,
            currency=currency,
            rate_date=use_date
        )

    def with_metadata(self, **kwargs) -> 'Transaction':
        """
        メタデータを追加した新しいトランザクションを作成
        
        Args:
            **kwargs: 追加するメタデータのキーワード引数
            
        Returns:
            新しいTransactionインスタンス
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
            metadata=new_metadata
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