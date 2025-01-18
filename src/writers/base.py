from abc import ABC, abstractmethod
from typing import List, Any
from pathlib import Path

class BaseWriter(ABC):
    """基本出力クラス"""
    
    def __init__(self, output_path: Path = None, encoding: str = 'utf-8'):
        self.output_path = output_path
        self.encoding = encoding
    
    @abstractmethod
    def write(self, records: List[Any]) -> None:
        """レコードを出力"""
        pass
    
    def _ensure_output_directory(self):
        """出力ディレクトリを確認・作成"""
        if self.output_path:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
