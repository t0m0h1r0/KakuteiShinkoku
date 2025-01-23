import csv
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Union
from pathlib import Path

from .currency import Currency
from .exchange_rate import ExchangeRate
from ..config.settings import DEFAULT_EXCHANGE_RATE, EXCHANGE_RATE_FILE

class RateProvider:
    """為替レートを提供するシングルトンクラス"""
    _instance = None
    _initialized = False
    _rate_file = None

    def __new__(cls, rate_file: Optional[Union[str, Path]] = None):
        if cls._instance is None:
            cls._instance = super(RateProvider, cls).__new__(cls)
        
        if not cls._initialized or (rate_file and str(rate_file) != cls._rate_file):
            if rate_file is None:
                rate_file = EXCHANGE_RATE_FILE if not cls._rate_file else cls._rate_file
            
            cls._instance._initialize(rate_file)
        
        return cls._instance

    def _initialize(self, rate_file: Union[str, Path]):
        """初期化処理"""
        self._rate_file = str(rate_file)
        self._rates: Dict[Currency, Dict[Currency, List[ExchangeRate]]] = {}
        
        self._setup_default_rates()
        
        try:
            self._load_rates(self._rate_file)
            RateProvider._initialized = True
        except Exception as e:
            print(f"Warning: Failed to load exchange rates: {e}")
            RateProvider._initialized = True

    def _setup_default_rates(self):
        """デフォルトレートの設定"""
        default_date = date.today()
        default_rates = {
            (Currency.USD, Currency.JPY): Decimal('150.0'),
            (Currency.USD, Currency.EUR): Decimal('0.9'),
            (Currency.USD, Currency.GBP): Decimal('0.8')
        }
        
        for base_curr in Currency.supported_currencies():
            if base_curr not in self._rates:
                self._rates[base_curr] = {}
            
            for target_curr in Currency.supported_currencies():
                if base_curr == target_curr:
                    continue
                    
                rate_value = default_rates.get(
                    (base_curr, target_curr),
                    Decimal('1.0')
                )
                
                self._rates[base_curr][target_curr] = [
                    ExchangeRate(
                        base_currency=base_curr,
                        target_currency=target_curr,
                        rate=rate_value,
                        date=default_date
                    )
                ]

    def get_rate(self, 
                 base_currency: Currency, 
                 target_currency: Currency, 
                 rate_date: Optional[date] = None) -> ExchangeRate:
        """為替レートの取得"""
        if rate_date is None:
            rate_date = date.today()

        # 同一通貨の場合
        if base_currency == target_currency:
            return ExchangeRate(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=Decimal('1.0'),
                date=rate_date
            )

        # クロスレートの計算
        if base_currency != Currency.USD:
            usd_base = self.get_rate(Currency.USD, base_currency, rate_date)
            usd_target = self.get_rate(Currency.USD, target_currency, rate_date)
            return ExchangeRate(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=usd_target.rate / usd_base.rate,
                date=rate_date
            )

        # USDベースのレート取得
        if (base_currency in self._rates and 
            target_currency in self._rates[base_currency]):
            matching_rates = [
                rate for rate in self._rates[base_currency][target_currency]
                if rate.date <= rate_date
            ]

            if matching_rates:
                return max(matching_rates, key=lambda r: r.date)

        # デフォルトレートを返却
        default_rates = {
            (Currency.USD, Currency.JPY): Decimal('150.0'),
            (Currency.USD, Currency.EUR): Decimal('0.9'),
            (Currency.USD, Currency.GBP): Decimal('0.8')
        }

        return ExchangeRate(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=default_rates.get((base_currency, target_currency), Decimal('1.0')),
            date=rate_date
        )

    def clear_cache(self):
        """キャッシュのクリア"""
        RateProvider._initialized = False
        self._rates.clear()
        self._rate_file = None