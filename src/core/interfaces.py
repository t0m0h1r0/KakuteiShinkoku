from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Any
from datetime import date

class IProcessor(ABC):
    """データ処理の基本インターフェース"""
    
    @abstractmethod
    def process(self, transaction: Any) -> None:
        """単一トランザクションを処理"""
        pass

    @abstractmethod
    def process_all(self, transactions: List[Any]) -> List[Any]:
        """複数トランザクションを処理"""
        pass

class ITransactionLoader(ABC):
    """トランザクション読み込みの基本インターフェース"""
    
    @abstractmethod
    def load(self, source: str) -> List[Any]:
        """データソースからトランザクションを読み込む"""
        pass

class IExchangeRateProvider(ABC):
    """為替レート提供の基本インターフェース"""
    
    @abstractmethod
    def get_rate(self, target_date: date) -> Decimal:
        """指定日の為替レートを取得"""
        pass

class IWriter(ABC):
    """出力処理の基本インターフェース"""
    
    @abstractmethod
    def write(self, records: List[Any]) -> None:
        """レコードを出力"""
        pass

class IPositionManager(ABC):
    """ポジション管理の基本インターフェース"""
    
    @abstractmethod
    def update_position(self, transaction: Any) -> None:
        """ポジションを更新"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Any]:
        """現在のポジションを取得"""
        pass