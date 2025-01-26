# core/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Processor(ABC):
    """データ処理の基本インターフェース"""
    
    @abstractmethod
    def process(self, transaction: Any) -> None:
        """単一トランザクションを処理"""
        pass

    @abstractmethod
    def process_all(self, transactions: List[Any]) -> List[Any]:
        """複数トランザクションを処理"""
        pass

class Loader(ABC):
    """データ読み込みの基本インターフェース"""
    
    @abstractmethod
    def load(self, source: str) -> List[Any]:
        """データソースからデータを読み込む"""
        pass

class Writer(ABC):
    """データ書き出しの基本インターフェース"""
    
    @abstractmethod
    def write(self, records: List[Any]) -> None:
        """レコードを出力"""
        pass

class PositionManager(ABC):
    """ポジション管理の基本インターフェース"""
    
    @abstractmethod
    def update(self, transaction: Any) -> None:
        """ポジションを更新"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Any]:
        """現在のポジションを取得"""
        pass