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
        """シングルトンパターンの実装"""
        if cls._instance is None:
            cls._instance = super(RateProvider, cls).__new__(cls)
        
        # 初回初期化時、またはファイルが指定された場合
        if not cls._initialized or (rate_file and str(rate_file) != cls._rate_file):
            # ファイル名が指定されていない場合は、既存のファイル名を使用
            if rate_file is None:
                # まだ初期化されていない場合はデフォルトファイルを使用
                if not cls._rate_file:
                    rate_file = EXCHANGE_RATE_FILE
                else:
                    rate_file = cls._rate_file
            
            cls._instance._initialize(rate_file)
        
        return cls._instance

    def _initialize(self, rate_file: Union[str, Path]):
        """初期化メソッド"""
        self._rate_file = str(rate_file)
        self._rates: Dict[Currency, Dict[Currency, List[ExchangeRate]]] = {}
        
        # デフォルトの為替レートを設定
        self._setup_default_rates()
        
        try:
            # ファイルから為替レートをロード
            self._load_rates(self._rate_file)
            RateProvider._initialized = True
        except Exception as e:
            print(f"Warning: Failed to load exchange rates from file: {e}")
            # 初期化に失敗した場合もフラグを設定
            RateProvider._initialized = True

    def _setup_default_rates(self):
        """デフォルトの為替レートを設定"""
        default_date = date.today()
        for base_currency in [Currency.USD]:
            if base_currency not in self._rates:
                self._rates[base_currency] = {}
            
            for target_currency in [Currency.JPY, Currency.EUR, Currency.GBP]:
                # デフォルトレートを設定
                default_rates = {
                    (Currency.USD, Currency.JPY): Decimal('150.0'),
                    (Currency.USD, Currency.EUR): Decimal('0.9'),
                    (Currency.USD, Currency.GBP): Decimal('0.8')
                }
                
                self._rates[base_currency][target_currency] = [
                    ExchangeRate(
                        base_currency=base_currency,
                        target_currency=target_currency,
                        rate=default_rates.get((base_currency, target_currency), Decimal('1.0')),
                        date=default_date
                    )
                ]

    def _parse_date(self, date_str: str) -> date:
        """日付文字列をパース"""
        # 様々な日付形式に対応
        date_formats = [
            '%m/%d/%y',   # 02/13/23
            '%m/%d/%Y',   # 01/23/2024 (デフォルト)
            '%Y-%m-%d',   # YYYY-MM-DD
            '%Y/%m/%d',   # 2024/01/23
            '%d/%m/%Y',   # 23/01/2024
        ]
        
        # 短縮年の処理（2桁の年を4桁に変換）
        def convert_two_digit_year(year_str: str) -> str:
            year = int(year_str)
            current_year = date.today().year % 100
            century = date.today().year - (date.today().year % 100)
            
            # 50年ルール：50以下の年は20xx、50より大きい年は19xx
            if year <= current_year:
                return str(century + year)
            else:
                return str(century - 100 + year)

        # 日付文字列から年の部分を抽出して変換
        parts = date_str.split('/')
        if len(parts) == 3 and len(parts[2]) == 2:
            parts[2] = convert_two_digit_year(parts[2])
            date_str = '/'.join(parts)
        
        # 日付をパース
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"サポートされない日付形式: {date_str}")

    def _load_rates(self, rate_file: str):
        """為替レートをファイルからロード"""
        try:
            with open(rate_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._process_rate_row(row)

            # 最低でも1年分のデータがない場合は警告
            if not any(r.date > (date.today() - date(date.today().year, 1, 1)) 
                       for target_rates in self._rates.values() 
                       for currency_rates in target_rates.values() 
                       for r in currency_rates):
                print(f"Warning: No recent exchange rates found in {rate_file}")

        except FileNotFoundError:
            raise FileNotFoundError(f"Rate file not found: {rate_file}")
        except Exception as e:
            raise RuntimeError(f"Error loading rate file {rate_file}: {e}")

    def _process_rate_row(self, row: Dict[str, str]):
        """CSVの1行から為替レートを処理"""
        try:
            # 日付をパース
            rate_date = self._parse_date(row['Date'])
            
            # 終値（Close）を為替レートとして使用
            # JPYレートはUSD/JPYのため、そのまま使用
            rate = Decimal(str(float(row['Close'].strip())))
            
            # USD→JPYのレートを追加
            self._add_rate(
                base_currency=Currency.USD, 
                target_currency=Currency.JPY, 
                rate=rate, 
                date=rate_date
            )

        except (ValueError, KeyError) as e:
            # エラーが発生した場合、詳細なエラー情報を出力
            print(f"Error processing rate row: {e}. Row data: {row}")

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
        
        # 同じ日付のレートは上書き
        existing_rates = [r for r in self._rates[base_currency][target_currency] if r.date == date]
        if existing_rates:
            existing_rates[0] = ExchangeRate(
                base_currency=base_currency,
                target_currency=target_currency,
                rate=rate,
                date=date
            )
        else:
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
        rate_date: Optional[date] = None
    ) -> ExchangeRate:
        """指定された条件の為替レートを取得"""
        if rate_date is None:
            rate_date = date.today()

        # レートの検索
        if (base_currency in self._rates and 
            target_currency in self._rates[base_currency]):
            
            # 日付で最も近いレートを検索
            matching_rates = [
                rate for rate in self._rates[base_currency][target_currency]
                if rate.date <= rate_date
            ]

            if matching_rates:
                # 最も最近の日付のレートを選択
                selected_rate = max(matching_rates, key=lambda r: r.date)
                print(f"Using exchange rate of {selected_rate.rate:.2f} on {selected_rate.date} for {base_currency} to {target_currency}")
                return selected_rate

        # レートが見つからない場合はデフォルトレートを返す
        print(f"Warning: Using default rate for {base_currency} to {target_currency}")
        
        # デフォルトレートを返す
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
        """キャッシュをクリア（テストや再初期化に使用）"""
        RateProvider._initialized = False
        self._rates.clear()
        self._rate_file = None