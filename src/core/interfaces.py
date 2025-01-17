from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional
from datetime import date
from ..core.models import Transaction, DividendRecord, TradeRecord

class IProcessor(ABC):
    """データ処理の基本インターフェース"""
    
    @abstractmethod
    def process(self, transaction: Transaction) -> None:
        """単一トランザクションを処理"""
        pass

class ITransactionLoader(ABC):
    """トランザクション読み込みの基本インターフェース"""
    
    @abstractmethod
    def load(self, source: str) -> List[Transaction]:
        """データソースからトランザクションを読み込む"""
        pass

class IExchangeRateProvider(ABC):
    """為替レート提供の基本インターフェース"""
    
    @abstractmethod
    def get_rate(self, date: date) -> Decimal:
        """指定日の為替レートを取得"""
        pass

class IWriter(ABC):
    """出力処理の基本インターフェース"""
    
    @abstractmethod
    def write(self, records: List[any]) -> None:
        """レコードを出力"""
        pass

class IPositionManager(ABC):
    """ポジション管理の基本インターフェース"""
    
    @abstractmethod
    def update_position(self, transaction: Transaction) -> None:
        """ポジションを更新"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Decimal]:
        """現在のポジションを取得"""
        pass
