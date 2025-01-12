from datetime import datetime
from decimal import Decimal
from pathlib import Path
import csv
import logging

from ..constants import DEFAULT_EXCHANGE_RATE, DATE_FORMAT, CSV_ENCODING

class ExchangeRateManager:
    """為替レートの管理を行うクラス"""
    
    def __init__(self, filename: str = 'HistoricalPrices.csv'):
        self.rates: Dict[str, Decimal] = {}
        self._load_rates(filename)

    def _load_rates(self, filename: str) -> None:
        """為替レートファイルを読み込む"""
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
        """日付文字列を標準形式に変換"""
        month, day, year = date_str.split('/')
        return f"{month}/{day}/{'20' + year if len(year) == 2 else year}"

    def get_rate(self, date: str) -> Decimal:
        """指定日付の為替レートを取得"""
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
