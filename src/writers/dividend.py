from decimal import Decimal
from pathlib import Path
from typing import Dict, List
import csv

from ..config import CSV_ENCODING, OUTPUT_DIR
from ..models.records import DividendRecord
from .base import ReportWriter

class DividendReportWriter(ReportWriter):
    """配当レポートをCSV形式で出力するクラス"""

    def __init__(self, filename: str):
        self.filepath = OUTPUT_DIR / filename

    def write(self, records: List[DividendRecord]) -> None:
        """CSVファイルにレポートを出力"""
        fieldnames = [
            'date', 'account', 'symbol', 'description', 'type',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ]
        
        with self.filepath.open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(self._format_record(record))

    @staticmethod
    def _format_record(record: DividendRecord) -> Dict:
        """配当記録をCSV出力用に整形"""
        return {
            'date': record.date,
            'account': record.account,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.type,
            'gross_amount_usd': round(record.gross_amount, 2),
            'tax_usd': round(record.tax, 2),
            'net_amount_usd': record.net_amount_usd,
            'exchange_rate': record.exchange_rate,
            'gross_amount_jpy': round(record.gross_amount * record.exchange_rate),
            'tax_jpy': round(record.tax * record.exchange_rate),
            'net_amount_jpy': record.net_amount_jpy,
            'reinvested': 'Yes' if record.reinvested else 'No'
        }
