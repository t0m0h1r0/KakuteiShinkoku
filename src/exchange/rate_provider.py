import csv
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from .currency import Currency
from .exchange_rate import ExchangeRate
from ..config.settings import EXCHANGE_RATE_FILE

class RateProvider:
    """為替レートを提供するシングルトンクラス"""
    _instance = None
    _initialized = False

    def __new__(cls):
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(RateProvider, cls).__new__(cls)
        return cls._instance

    def __init__(self, rate_file: Optional[str] = None):
        """初期化メソッド"""
        if not RateProvider._initialized:
            self._rates: Dict[Currency, Dict[Currency, List[ExchangeRate]]] = {}
            self._load_rates(rate_file or str(EXCHANGE_RATE_FILE))
            RateProvider._initialized = True

    def _load_rates(self, rate_file: str):
        """為替レートをファイルからロード"""
        try:
            with open(rate_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._process_rate_row(row)
        except FileNotFoundError:
            print(f"Warning: Rate file {rate_file} not found.")
        except Exception as e:
            print(f"Error loading rate file: {e}")

    def _process_rate_row(self, row: Dict[str, str]):
        """CSVの1行から為替レートを処理"""
        try:
            rate_date = date.fromisoformat(row['Date'])
            
            # USD→他通貨のレートを追加
            for target_currency in [Currency.JPY, Currency.EUR, Currency.GBP]:
                rate = Decimal(row[' Close'])  # スペースに注意
                self._add_rate(
                    base_currency=Currency.USD, 
                    target_currency=target_currency, 
                    rate=rate, 
                    date=rate_date
                )

        except (ValueError, KeyError) as e:
            print(f"Error processing rate row: {e}")

    def _add_rate(
        self, 
        base_currency: Currency, 
        target_currency: Currency, 
        rate: Decimal, 
        date: date
    ):
        """為替レートを内部辞書に追加"""
        if base_currency not in self._rates:
            self._rates[base_currency] = {}
        
        if target_currency not in self._rates[base_currency]:
            self._rates[base_currency][target_currency] = []
        
        self._rates[base_currency][target_currency].append(
            ExchangeRate(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=rate,
                date=date
            )
        )

    def get_rate(
        self, 
        base_currency: Currency, 
        target_currency: Currency, 
        date: Optional[date] = None
    ) -> Optional[ExchangeRate]:
        """指定された条件の為替レートを取得"""
        if date is None:
            date = date.today()

        # レートの検索
        if (base_currency in self._rates and 
            target_currency in self._rates[base_currency]):
            
            # 日付で最も近いレートを検索
            matching_rates = [
                rate for rate in self._rates[base_currency][target_currency]
                if rate.date <= date
            ]

            if matching_rates:
                # 最も最近の日付のレートを選択
                return max(matching_rates, key=lambda r: r.date)

        # レートが見つからない場合のデフォルト処理
        print(f"Warning: No exchange rate found for {base_currency} to {target_currency}")
        
        # デフォルトレートを返す（実際のアプリケーションでは設定から取得）
        default_rates = {
            (Currency.USD, Currency.JPY): Decimal('150.0'),
            (Currency.USD, Currency.EUR): Decimal('0.9'),
            (Currency.USD, Currency.GBP): Decimal('0.8')
        }

        return ExchangeRate(
            base_currency=base_currency,
            target_currency=target_currency,
            rate=default_rates.get((base_currency, target_currency), Decimal('1.0')),
            date=date
        )

    def clear_cache(self):
        """キャッシュをクリア（テストや再初期化に使用）"""
        self._rates.clear()
        RateProvider._initialized = False