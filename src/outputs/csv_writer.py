from pathlib import Path
from typing import List, Dict, Any
import csv
import logging
from decimal import Decimal

from .base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter
from ..exchange.money import Money, Currency

class CSVWriter(BaseOutput):
    """CSV出力クラス"""
    
    def __init__(self, output_path: Path, fieldnames: List[str], 
                 encoding: str = 'utf-8'):
        super().__init__()
        self.output_path = output_path
        self.fieldnames = fieldnames
        self.encoding = encoding
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def output(self, records: List[Dict[str, Any]]) -> None:
        """レコードをCSVに出力"""
        try:
            # 出力ディレクトリの作成
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # レコードのフォーマット処理
            formatted_records = [
                self._format_record(record) for record in records
            ]
            
            with self.output_path.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(formatted_records)
            
            self.logger.info(f"Successfully wrote {len(records)} records to {self.output_path}")
        
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {e}")
            raise

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """レコードのフォーマット処理"""
        formatted = {}
        
        for field in self.fieldnames:
            value = record.get(field, '')
            
            # 金額フィールドの特別処理
            if field.endswith('_jpy') and value:
                formatted[field] = self._format_jpy_amount(value)
            elif field.endswith(('amount', 'price', 'gain', 'pnl', 'fees')):
                formatted[field] = self._format_usd_amount(value)
            elif isinstance(value, Money):
                # Money型の場合は金額のみを取り出す
                if value.currency == Currency.JPY:
                    formatted[field] = self._format_jpy_amount(value.amount)
                else:
                    formatted[field] = self._format_usd_amount(value.amount)
            else:
                formatted[field] = value
        
        return formatted

    def _format_usd_amount(self, value: Any) -> str:
        """USD金額のフォーマット"""
        if not value:
            return ''
        if isinstance(value, Money):
            value = value.amount
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            return f"{value:.2f}"
        return str(value)

    def _format_jpy_amount(self, value: Any) -> str:
        """JPY金額のフォーマット"""
        if not value:
            return ''
        if isinstance(value, Money):
            value = value.amount
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            return str(int(value))
        return str(value)