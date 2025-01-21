from abc import ABC, abstractmethod
from typing import Dict, Any, List

class ReportGeneratorInterface(ABC):
    """レポート生成インターフェース"""
    
    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """指定されたデータからレポートを生成"""
        pass

class ReportWriterInterface(ABC):
    """レポート書き出しインターフェース"""
    
    @abstractmethod
    def output(self, records: List[Dict[str, Any]]) -> None:
        """レポートを指定された出力先に書き出す"""
        pass

class BaseReportGenerator(ReportGeneratorInterface):
    """レポート生成の基本実装"""
    
    def __init__(self, writer):
        self.writer = writer

    def generate_and_write(self, data: Dict[str, Any]) -> None:
        """レポートの生成と書き出しを行う"""
        records = self.generate(data)
        self.writer.output(records)  # writeからoutputに変更

    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """レポート生成の抽象メソッド"""
        pass