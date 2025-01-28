from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, TypeVar, Generic, Optional
import logging
from contextlib import contextmanager

T = TypeVar('T')

class BaseReportGenerator(Generic[T], ABC):
    """
    レポート生成の基本インターフェース
    
    汎用的なレポート生成とエラーハンドリングを提供する抽象基本クラス。
    """
    
    def __init__(self, writer: Any):
        """
        初期化メソッド
        
        Args:
            writer: レポートを書き出すライター
        """
        self.writer = writer
        self.logger = logging.getLogger(self.__class__.__name__)

    @contextmanager
    def _error_handling(self, operation: str):
        """
        エラーハンドリングのコンテキストマネージャ
        
        Args:
            operation: エラーが発生した操作の説明
        """
        try:
            yield
        except Exception as e:
            self.logger.error(f"{operation}中にエラーが発生: {e}", exc_info=True)
            raise

    def generate_and_write(self, data: Dict[str, Any]) -> Optional[List[T]]:
        """
        レポートの生成と書き出しを行う
        
        Args:
            data: レポート生成に必要なデータ
        
        Returns:
            生成されたレコードのリスト、エラー時はNone
        """
        with self._error_handling("レポート生成"):
            records = self.generate(data)
            
            with self._error_handling("レポート書き出し"):
                self.writer.output(records)
            
            return records

    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> List[T]:
        """
        レポート生成の抽象メソッド
        
        Args:
            data: レポート生成に必要なデータ
        
        Returns:
            生成されたレコードのリスト
        """
        pass