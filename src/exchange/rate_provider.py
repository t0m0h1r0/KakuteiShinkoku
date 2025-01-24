# rate_provider.py
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Union  
import csv
import logging

from .currency import Currency
from .exchange_rate import ExchangeRate

class ExchangePair:
   def __init__(self, base: Currency, target: Currency, default_rate: Decimal, history_file: Optional[Path] = None):
       self.base = base
       self.target = target
       self.default_rate = default_rate
       self.history_file = history_file
       self.rates: List[ExchangeRate] = []
       self.logger = logging.getLogger(self.__class__.__name__)

   def load_rates(self) -> None:
       if not self.history_file or not self.history_file.exists():
           return

       try:
           with open(self.history_file, 'r', encoding='utf-8') as csvfile:
               reader = csv.DictReader(line.replace(' ', '') for line in csvfile)
               for row in reader:
                   try:
                       rate_date = datetime.strptime(row['Date'], '%m/%d/%y').date()
                       rate = ExchangeRate(
                           base_currency=self.base,
                           target_currency=self.target,
                           rate=Decimal(row['Close']),
                           date=rate_date
                       )
                       self.rates.append(rate)
                   except Exception as e:
                       self.logger.warning(f"Could not parse rate for {row.get('Date', 'unknown date')}: {e}")

               self.rates.sort(key=lambda x: x.date)
       except Exception as e:
           self.logger.error(f"Error loading exchange rates from {self.history_file}: {e}")

class RateProvider:
   _instance = None
   _initialized = False

   def __new__(cls):
       if cls._instance is None:
           cls._instance = super(RateProvider, cls).__new__(cls)
       return cls._instance

   def __init__(self):
       if not self._initialized:
           self._pairs: Dict[tuple[Currency, Currency], ExchangePair] = {}
           RateProvider._initialized = True

   def initialize(self, pairs: List[ExchangePair]) -> None:
       self._pairs.clear()
       for pair in pairs:
           pair.load_rates()
           self._pairs[(pair.base, pair.target)] = pair

   def get_rate(self, base_currency: Currency, target_currency: Currency, rate_date: date) -> ExchangeRate:
       if base_currency == target_currency:
           return ExchangeRate(
               base_currency=base_currency,
               target_currency=target_currency,
               rate=Decimal('1.0'),
               date=rate_date
           )

       pair = self._get_exchange_pair(base_currency, target_currency)
       if not pair:
           return self._create_default_rate(base_currency, target_currency, rate_date)

       matching_rates = [rate for rate in pair.rates if rate.date <= rate_date]
       if matching_rates:
           return max(matching_rates, key=lambda r: r.date)

       return ExchangeRate(
           base_currency=pair.base,
           target_currency=pair.target,
           rate=pair.default_rate,
           date=rate_date
       )

   def _get_exchange_pair(self, base: Currency, target: Currency) -> Optional[ExchangePair]:
       direct_pair = self._pairs.get((base, target))
       if direct_pair:
           return direct_pair

       inverse_pair = self._pairs.get((target, base))
       if inverse_pair:
           return inverse_pair

       # USDを経由したクロスレート対応
       if base != Currency.USD and target != Currency.USD:
           usd_base = self._pairs.get((Currency.USD, base))
           usd_target = self._pairs.get((Currency.USD, target))
           if usd_base and usd_target:
               return ExchangePair(
                   base=base,
                   target=target,
                   default_rate=usd_target.default_rate / usd_base.default_rate
               )

       return None

   def _create_default_rate(self, base: Currency, target: Currency, rate_date: date) -> ExchangeRate:
       return ExchangeRate(
           base_currency=base,
           target_currency=target,
           rate=Decimal('1.0'),
           date=rate_date
       )

   def clear_cache(self):
       self._pairs.clear()