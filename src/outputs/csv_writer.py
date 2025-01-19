from pathlib import Path
from typing import List, Dict, Any
import csv
import logging

from .base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter

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
            
            with self.output_path.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(records)
            
            self.logger.info(f"Successfully wrote {len(records)} records to {self.output_path}")
        
        except Exception as e:
            self.logger.error(f"Error writing to CSV: {e}")
            raise

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """必要に応じてレコードをフォーマット"""
        return {
            field: record.get(field, '') 
            for field in self.fieldnames
        }