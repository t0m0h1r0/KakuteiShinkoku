# exchange/exchange.py

from datetime import date
from decimal import Decimal
from pathlib import Path
import csv
import logging
from typing import Optional
from datetime import datetime

from .currency import Currency
from .rate import Rate

class ExchangeService:
   """為替変換サービス"""
   def __init__(self):
       self._default_rate = Decimal('150.0')  # USD/JPY デフォルト
       self._rates = {}
       self.logger = logging.getLogger(self.__class__.__name__)

   def convert(self, amount: Decimal, from_currency: Currency, to_currency: Currency, rate_date: Optional[date] = None) -> Decimal:
       """通貨を変換"""
       if rate_date is None:
           rate_date = date.today()

       rate = self.get_rate(from_currency, to_currency, rate_date)
       return rate.convert(amount)

   def get_rate(self, base: Currency, target: Currency, rate_date: date) -> Rate:
       """為替レートを取得"""
       if base == target:
           return Rate(base, target, Decimal('1'), rate_date)

       rate_key = (base, target, rate_date)
       if rate_key in self._rates:
           return self._rates[rate_key]

       rate_value = self._default_rate if (base == Currency.USD and target == Currency.JPY) else (Decimal('1') / self._default_rate)
       return Rate(base, target, rate_value, rate_date)

   def add_rate_source(self, base: Currency, target: Currency, default_rate: Decimal, history_file: Optional[Path] = None):
       """レートソースを追加"""
       self._default_rate = default_rate
       if history_file and history_file.exists():
           self._load_rates(base, target, history_file)

   def _load_rates(self, base: Currency, target: Currency, file_path: Path) -> None:
       """CSVからレートを読み込み"""
       try:
           with open(file_path, 'r', encoding='utf-8') as f:
               reader = csv.DictReader(line.replace(' ', '') for line in f)
               for row in reader:
                   try:
                       rate_date = datetime.strptime(row['Date'], '%m/%d/%y').date()
                       rate_value = Decimal(row['Close'])
                       rate = Rate(base, target, rate_value, rate_date)
                       self._rates[(base, target, rate_date)] = rate
                   except Exception as e:
                       self.logger.warning(f"レート解析エラー: {e}")
       except Exception as e:
           self.logger.error(f"レート読み込みエラー: {e}")

# グローバルインスタンス
exchange = ExchangeService()