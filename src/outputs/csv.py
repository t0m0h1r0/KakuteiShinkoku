from pathlib import Path
from typing import List, Dict, Any
from decimal import Decimal
import csv
import logging
from .base import BaseOutput

class CSVOutput(BaseOutput):
   def __init__(self, output_path: Path, fieldnames: List[str], encoding: str = 'utf-8'):
       super().__init__()
       self.output_path = output_path
       self.fieldnames = fieldnames
       self.encoding = encoding

   def output(self, records: List[Dict[str, Any]]) -> None:
       try:
           self.output_path.parent.mkdir(parents=True, exist_ok=True)
           formatted_records = [self._format_record(record) for record in records]
           
           with self.output_path.open('w', newline='', encoding=self.encoding) as f:
               writer = csv.DictWriter(f, fieldnames=self.fieldnames)
               writer.writeheader()
               writer.writerows(formatted_records)
           
           self.logger.info(f"{len(records)}件のレコードを{self.output_path}に出力")
       
       except Exception as e:
           self.logger.error(f"CSV出力エラー: {e}")
           raise

   def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
       formatted = {}
       
       for field in self.fieldnames:
           value = record.get(field, '')
           
           if not value:
               formatted[field] = ''
               continue

           if field.endswith('_jpy'):
               formatted[field] = self._format_jpy(value)
           elif field.endswith(('amount', 'price', 'gain', 'pnl', 'fees')):
               formatted[field] = self._format_usd(value)
           else:
               formatted[field] = str(value)
       
       return formatted

   def _format_usd(self, value: Any) -> str:
       if not value:
           return ''
       try:
           amount = Decimal(str(value))
           return f"{amount:,.2f}"
       except (TypeError, ValueError):
           return str(value)

   def _format_jpy(self, value: Any) -> str:
       if not value:
           return ''
       try:
           amount = Decimal(str(value))
           return f"{int(amount):,}"
       except (TypeError, ValueError):
           return str(value)