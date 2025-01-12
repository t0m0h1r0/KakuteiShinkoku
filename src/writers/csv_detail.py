# src/writers/csv_detail.py
from pathlib import Path
import csv
from typing import Dict, List
from decimal import Decimal
from .base import ReportWriter
from ..models.data_models import DividendRecord
from ..utils.constants import CSV_ENCODING

class CSVReportWriter(ReportWriter):
    def __init__(self, filename: str):
        self.filename = filename

    def write(self, records: List[DividendRecord]) -> None:
        fieldnames = [
            'date', 'account', 'symbol', 'description', 'type',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ]
        
        with Path(self.filename).open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(self._format_record(record))

    @staticmethod
    def _format_record(record: DividendRecord) -> Dict:
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

