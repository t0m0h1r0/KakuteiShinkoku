# core/base.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any, Optional
from datetime import date

T = TypeVar('T')
D = TypeVar('D')

class BaseHandler(ABC):
    """基本ハンドラーインターフェース"""
    
    @abstractmethod
    def handle(self, data: Any) -> Any:
        """データを処理"""
        pass

class Processor(Generic[T], BaseHandler):
    """データ処理の基本インターフェース"""
    
    @abstractmethod
    def process(self, data: T) -> None:
        """単一データを処理"""
        pass

    @abstractmethod
    def process_all(self, items: List[T]) -> List[Any]:
        """複数データを処理"""
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandler実装"""
        return self.process(data)

class Loader(Generic[D], BaseHandler):
    """データ読み込みの基本インターフェース"""
    
    @abstractmethod
    def load(self, source: str) -> List[D]:
        """データソースからデータを読み込む"""
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandler実装"""
        return self.load(data)

class Writer(Generic[D], BaseHandler):
    """データ書き出しの基本インターフェース"""
    
    @abstractmethod
    def write(self, records: List[D]) -> None:
        """レコードを出力"""
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandler実装"""
        return self.write(data)

class PositionManager(Generic[T], BaseHandler):
    """ポジション管理の基本インターフェース"""
    
    @abstractmethod
    def update(self, transaction: T) -> None:
        """ポジションを更新"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str, date: Optional[date] = None) -> Optional[Any]:
        """現在のポジションを取得"""
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandler実装"""
        return self.update(data)