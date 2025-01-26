from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseReportGenerator(ABC):
    def __init__(self, writer):
        self.writer = writer

    def generate_and_write(self, data: Dict[str, Any]) -> None:
        """レポートの生成と書き出しを行う"""
        records = self.generate(data)
        self.writer.output(records)

    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """レポート生成の抽象メソッド"""
        pass
