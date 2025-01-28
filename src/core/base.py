from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Any, Optional, Dict
from datetime import date
import logging

T = TypeVar('T')  # 処理対象データの型
D = TypeVar('D')  # データソースの型
R = TypeVar('R')  # 処理結果の型

class BaseHandler(ABC):
    """
    基本ハンドラーインターフェース
    
    全てのハンドラーの基底クラスとして機能し、
    共通のインターフェースを定義します。
    """
    
    def __init__(self) -> None:
        """ハンドラーを初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def handle(self, data: Any) -> Any:
        """
        データを処理する基本メソッド
        
        Args:
            data: 処理対象のデータ
            
        Returns:
            処理結果
        """
        pass

class DataProcessor(Generic[T, R], BaseHandler):
    """
    データ処理の基本インターフェース
    
    入力データを処理し、結果を生成する処理を定義します。
    """
    
    @abstractmethod
    def process(self, data: T) -> R:
        """
        単一データを処理
        
        Args:
            data: 処理対象のデータ
            
        Returns:
            処理結果
        """
        pass

    @abstractmethod
    def process_all(self, items: List[T]) -> List[R]:
        """
        複数データを一括処理
        
        Args:
            items: 処理対象のデータリスト
            
        Returns:
            処理結果のリスト
        """
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandlerインターフェースの実装"""
        return self.process(data)

class DataLoader(Generic[D], BaseHandler):
    """
    データ読み込みの基本インターフェース
    
    データソースからデータを読み込む処理を定義します。
    """
    
    @abstractmethod
    def load(self, source: str) -> List[D]:
        """
        データソースからデータを読み込む
        
        Args:
            source: データソースの指定
            
        Returns:
            読み込んだデータのリスト
        """
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandlerインターフェースの実装"""
        return self.load(data)

class DataWriter(Generic[D], BaseHandler):
    """
    データ書き出しの基本インターフェース
    
    データを出力先に書き出す処理を定義します。
    """
    
    @abstractmethod
    def write(self, records: List[D]) -> None:
        """
        レコードを出力
        
        Args:
            records: 出力するレコードのリスト
        """
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandlerインターフェースの実装"""
        return self.write(data)

class PositionManager(Generic[T], BaseHandler):
    """
    ポジション管理の基本インターフェース
    
    取引ポジションの管理と計算を行う処理を定義します。
    """
    
    @abstractmethod
    def update(self, transaction: T) -> None:
        """
        ポジションを更新
        
        Args:
            transaction: 更新のための取引データ
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str, date: Optional[date] = None) -> Optional[Any]:
        """
        現在のポジションを取得
        
        Args:
            symbol: 銘柄シンボル
            date: 参照日（オプション）
            
        Returns:
            ポジション情報、または None
        """
        pass

    def handle(self, data: Any) -> Any:
        """BaseHandlerインターフェースの実装"""
        return self.update(data)

class BaseProcessor(Generic[T, R]):
    """
    基本プロセッサクラス
    
    全てのプロセッサの基底クラスとして機能し、
    共通の処理機能を提供します。
    """
    
    def __init__(self) -> None:
        """プロセッサを初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()
    
    def _initialize(self) -> None:
        """内部状態を初期化"""
        self._processed_items: List[R] = []
        self._error_items: List[Dict[str, Any]] = []
    
    def process_item(self, item: T) -> Optional[R]:
        """
        単一アイテムを処理
        
        Args:
            item: 処理対象のアイテム
            
        Returns:
            処理結果、またはNone（エラー時）
        """
        try:
            result = self._process_impl(item)
            if result is not None:
                self._processed_items.append(result)
            return result
            
        except Exception as e:
            self.logger.error(f"処理エラー: {e}", exc_info=True)
            self._error_items.append({
                'item': item,
                'error': str(e)
            })
            return None
    
    @abstractmethod
    def _process_impl(self, item: T) -> Optional[R]:
        """
        実際の処理を実装するメソッド
        
        Args:
            item: 処理対象のアイテム
            
        Returns:
            処理結果、またはNone
        """
        pass
    
    @property
    def processed_items(self) -> List[R]:
        """処理済みアイテムのリストを取得"""
        return self._processed_items
    
    @property
    def error_items(self) -> List[Dict[str, Any]]:
        """エラーが発生したアイテムのリストを取得"""
        return self._error_items