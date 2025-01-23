from pathlib import Path
from typing import List, Dict, Any
import csv
import logging
from decimal import Decimal

from .base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter
from ..exchange.money import Money, Currency

class CSVWriter(BaseOutput):
    def __init__(self, output_path: Path, fieldnames: List[str], encoding: str = 'utf-8'):
        super().__init__()
        self.output_path = output_path
        self.fieldnames = fieldnames
        self.encoding = encoding
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def output(self, records: List[Dict[str, Any]]) -> None:
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            formatted_records = [self._format_record(record) for record in records]
            
            with self.output_path.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(formatted_records)
            
            self.logger.info(f"Successfully wrote {len(records)} records to {self.output_path}")
        
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {e}")
            raise

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        formatted = {}
        
        for field in self.fieldnames:
            value = record.get(field, '')
            
            if field.endswith('_jpy') and value:
                formatted[field] = self._format_jpy_amount(value)
            elif field.endswith(('amount', 'price', 'gain', 'pnl', 'fees')):
                formatted[field] = self._format_usd_amount(value)
            elif isinstance(value, Money):
                if value.display_currency == Currency.JPY:
                    formatted[field] = self._format_jpy_amount(value.jpy)
                else:
                    formatted[field] = self._format_usd_amount(value.usd)
            else:
                formatted[field] = value
        
        return formatted

    def _format_usd_amount(self, value: Any) -> str:
        if not value:
            return ''
        if isinstance(value, Money):
            value = value.usd
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            # 3桁ごとにカンマを追加し、小数点以下2桁を表示
            whole, decimal = f"{value:.2f}".split('.')
            whole = f"{int(whole):,}"
            return f"{whole}.{decimal}"
        return str(value)

    def _format_jpy_amount(self, value: Any) -> str:
        if not value:
            return ''
        if isinstance(value, Money):
            value = value.jpy
        if isinstance(value, (int, float)):
            value = Decimal(str(value))
        if isinstance(value, Decimal):
            # JPYは小数点以下なしで3桁ごとにカンマを追加
            return f"{int(value):,}"
        return str(value)