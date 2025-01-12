# src/processors/exchange_rate.py
from decimal import Decimal
import csv
import logging
from pathlib import Path
from datetime import datetime
from ..utils.constants import DEFAULT_EXCHANGE_RATE, DATE_FORMAT, CSV_ENCODING

class ExchangeRateManager:
    def __init__(self, filename: str = 'HistoricalPrices.csv'):
        self.rates: Dict[str, Decimal] = {}
        self._load_rates(filename)

    def _load_rates(self, filename: str) -> None:
        try:
            with Path(filename).open('r', encoding=CSV_ENCODING) as f:
                reader = csv.DictReader(f)
                self.rates = {
                    self._normalize_date(row['Date'].strip()): Decimal(row[' Close'])
                    for row in reader
                }
        except FileNotFoundError:
            logging.warning(f"為替レートファイル {filename} が見つかりません")
        except Exception as e:
            logging.error(f"為替レートファイルの読み込み中にエラー: {e}")

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        month, day, year = date_str.split('/')
        return f"{month}/{day}/{'20' + year if len(year) == 2 else year}"

    def get_rate(self, date: str) -> Decimal:
        if not self.rates:
            return DEFAULT_EXCHANGE_RATE

        if date in self.rates:
            return self.rates[date]

        target_date = datetime.strptime(date, DATE_FORMAT)
        dated_rates = {
            datetime.strptime(d, DATE_FORMAT): r 
            for d, r in self.rates.items()
        }

        previous_dates = [d for d in dated_rates.keys() if d <= target_date]
        return dated_rates[max(previous_dates)] if previous_dates else list(self.rates.values())[0]

