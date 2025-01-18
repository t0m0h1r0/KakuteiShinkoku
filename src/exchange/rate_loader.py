from pathlib import Path
from typing import Dict
from datetime import date, datetime
from decimal import Decimal
import csv
import logging

from ..config.settings import FILE_ENCODING

class RateLoadError(Exception):
    """レート読み込みエラー"""
    pass

class RateLoader:
    """為替レート読み込みクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_rates(self, rate_file: Path) -> Dict[date, Decimal]:
        """為替レートファイルを読み込む"""
        rates = {}
        try:
            with rate_file.open('r', encoding=FILE_ENCODING) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rate_date = self._parse_date(row['Date'].strip())
                        rate = Decimal(row[' Close'].strip())
                        rates[rate_date] = rate
                    except (ValueError, KeyError) as e:
                        self.logger.error(f"Error parsing rate data: {e}")
                        continue
            
            if not rates:
                raise RateLoadError("No rates were loaded")
            
            return rates
            
        except FileNotFoundError:
            raise RateLoadError(f"Exchange rate file not found: {rate_file}")
        except Exception as e:
            raise RateLoadError(f"Error loading exchange rates: {e}")

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """日付文字列をパース"""
        for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unsupported date format: {date_str}")
