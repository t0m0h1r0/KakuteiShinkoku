from pathlib import Path
from typing import List, Dict, Any
from decimal import Decimal
import csv
import logging

from .base import BaseOutput, BaseFormatter

class CSVFormatter(BaseFormatter):
    """CSV出力用フォーマッター"""
    
    def __init__(self, fieldnames: List[str]):
        super().__init__()
        self.fieldnames = fieldnames

    def format(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """レコードのフォーマット"""
        return [self._format_record(record) for record in records]

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        formatted = {}
        
        for field in self.fieldnames:
            value = record.get(field, '')
            
            if not value:
                formatted[field] = ''
                continue

            if field.endswith('_jpy'):
                formatted[field] = self.format_money(value, 'JPY')
            elif field.endswith(('amount', 'price', 'gain', 'pnl', 'fees')):
                formatted[field] = self.format_money(value, 'USD')
            else:
                formatted[field] = str(value)
        
        return formatted

class CSVOutput(BaseOutput):
    """CSV出力クラス"""
    
    def __init__(self, output_path: Path, fieldnames: List[str], encoding: str = 'utf-8'):
        formatter = CSVFormatter(fieldnames)
        super().__init__(formatter)
        self.output_path = output_path
        self.fieldnames = fieldnames
        self.encoding = encoding
        self.logger = logging.getLogger(self.__class__.__name__)

    def output(self, records: List[Dict[str, Any]]) -> None:
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            formatted_records = self._format_data(records)
            
            with self.output_path.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(formatted_records)
            
            self.logger.info(f"{len(records)}件のレコードを{self.output_path}に出力")
        
        except Exception as e:
            self.logger.error(f"CSV出力エラー: {e}")
            raise