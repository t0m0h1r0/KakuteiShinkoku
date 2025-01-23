import csv
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Union  
from pathlib import Path

from .currency import Currency
from .exchange_rate import ExchangeRate
DEFAULT_EXCHANGE_RATE = '150.0'

class RateProvider:
    """為替レートを提供するシングルトンクラス"""
    _instance = None
    _initialized = False
    _rate_file = None

    def __new__(cls, 
                rate_file: Optional[Union[str, Path]] = None,
                base_currency: Optional[Currency] = Currency.USD,
                target_currency: Optional[Currency] = Currency.JPY):
        if cls._instance is None:
            cls._instance = super(RateProvider, cls).__new__(cls)
        
        if not cls._initialized or (rate_file and str(rate_file) != cls._rate_file):
            # 通貨ペアの設定
            if base_currency and target_currency:
                cls._instance._base_currency = base_currency
                cls._instance._target_currency = target_currency
            else:
                cls._instance._base_currency = Currency.USD
                cls._instance._target_currency = Currency.JPY
            
            cls._instance._initialize(rate_file if rate_file else str(DEFAULT_EXCHANGE_RATE))
        
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

    def _load_rates(self, rate_file: Union[str, Path]):
        """為替レートCSVの読み込み"""
        try:
            with open(rate_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(line.replace(' ', '') for line in csvfile)
                
                # USD/JPYレートのみ対応
                base_curr = self._base_currency
                target_curr = self._target_currency
                
                if base_curr not in self._rates:
                    self._rates[base_curr] = {}
                
                if target_curr not in self._rates[base_curr]:
                    self._rates[base_curr][target_curr] = []
                
                # Closeレートを為替レートとして使用
                rates = []
                for row in reader:
                    try:
                        rate_date = datetime.strptime(row['Date'], '%m/%d/%y').date()
                        rate = ExchangeRate(
                            base_currency=base_curr,
                            target_currency=target_curr,
                            rate=Decimal(row['Close']),
                            date=rate_date
                        )
                        rates.append(rate)
                    except Exception as e:
                        print(f"Warning: Could not parse rate for {row.get('Date', 'unknown date')}: {e}")
                
                # レートをリストに追加
                self._rates[base_curr][target_curr] = rates
                
                # レートを日付順にソート
                for base_curr in self._rates:
                    for target_curr in self._rates[base_curr]:
                        self._rates[base_curr][target_curr].sort(key=lambda x: x.date)

        except FileNotFoundError:
            print(f"Warning: Exchange rate file not found: {rate_file}")
        except Exception as e:
            print(f"Error loading exchange rates: {e}")

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
                # 最も近い日付のレートを取得
                return max(matching_rates, key=lambda r: r.date)

        # デフォルトレートを返却
        return ExchangeRate(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=DEFAULT_EXCHANGE_RATE,
            date=rate_date
        )

    def clear_cache(self):
        """キャッシュのクリア"""
        RateProvider._initialized = False
        self._rates.clear()
        self._rate_file = None

    @property
    def base_currency(self) -> Currency:
        """基準通貨を取得"""
        return self._base_currency

    @property
    def target_currency(self) -> Currency:
        """対象通貨を取得"""
        return self._target_currency