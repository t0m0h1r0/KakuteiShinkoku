from pathlib import Path
from typing import List, Dict, Any
import csv
import logging

from .base import BaseWriter

class CSVWriter(BaseWriter):
    """CSV出力クラス"""
    
    def __init__(self, output_path: Path, fieldnames: List[str], 
                 encoding: str = 'utf-8'):
        super().__init__(output_path, encoding)
        self.fieldnames = fieldnames
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def write(self, records: List[Dict[str, Any]]) -> None:
        """レコードをCSVに出力"""
        try:
            self._ensure_output_directory()
            
            with self.output_path.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                writer.writerows(records)
            
            self._logger.info(f"Successfully wrote {len(records)} records to {self.output_path}")
        
        except Exception as e:
            self._logger.error(f"Error writing to CSV: {e}")
            raise

    def _format_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """必要に応じてレコードをフォーマット"""
        return {
            field: record.get(field, '') 
            for field in self.fieldnames
        }
