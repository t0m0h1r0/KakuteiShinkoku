from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Dict, Optional
import csv
import logging
from functools import lru_cache

from ..core.interfaces import IExchangeRateProvider
from ..config.settings import FILE_ENCODING, DEFAULT_EXCHANGE_RATE
from ..config.constants import Currency

class ExchangeRateError(Exception):
    """為替レート関連のエラー"""
    pass

class ExchangeRateProvider(IExchangeRateProvider):
    """為替レート提供クラス"""
    
    def __init__(self, rate_file: Path, cache_size: int = 1000):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._rates: Dict[date, Decimal] = {}
        self._rate_file = rate_file
        self._cache_size = cache_size
        self._load_rates()

    def get_rate(self, target_date: date) -> Decimal:
        """指定日の為替レートを取得"""
        try:
            return self._get_cached_rate(target_date)
        except ExchangeRateError as e:
            self._logger.warning(f"Exchange rate fetch failed: {e}")
            return DEFAULT_EXCHANGE_RATE

    @lru_cache(maxsize=1000)
    def _get_cached_rate(self, target_date: date) -> Decimal:
        """キャッシュを使用して為替レートを取得"""
        if not self._rates:
            raise ExchangeRateError("No exchange rates available")

        if target_date in self._rates:
            return self._rates[target_date]

        # 直近の為替レートを探す
        closest_date = self._find_closest_date(target_date)
        if closest_date:
            return self._rates[closest_date]
        
        raise ExchangeRateError(f"No exchange rate found for date: {target_date}")

    def _load_rates(self) -> None:
        """為替レートファイルを読み込む"""
        try:
            with self._rate_file.open('r', encoding=FILE_ENCODING) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rate_date = self._parse_date(row['Date'].strip())
                        rate = Decimal(row[' Close'].strip())
                        self._rates[rate_date] = rate
                    except (ValueError, KeyError, decimal.InvalidOperation) as e:
                        self._logger.error(f"Error parsing rate data: {e}")
                        continue
            
            self._validate_loaded_rates()
            
        except FileNotFoundError:
            self._logger.error(f"Exchange rate file not found: {self._rate_file}")
        except Exception as e:
            self._logger.error(f"Error loading exchange rates: {e}")

    def _validate_loaded_rates(self) -> None:
        """読み込んだレートのバリデーション"""
        if not self._rates:
            self._logger.warning("No exchange rates were loaded")
            return

        # 異常値のチェック
        avg_rate = sum(self._rates.values()) / len(self._rates)
        threshold = Decimal('30')  # 平均値から30%以上離れているレートを検出
        
        for date_, rate in self._rates.items():
            if abs((rate - avg_rate) / avg_rate) > threshold / 100:
                self._logger.warning(
                    f"Potentially anomalous rate detected: {date_}, rate: {rate}"
                )

    def _find_closest_date(self, target_date: date) -> Optional[date]:
        """指定日に最も近い日付を探す"""
        if not self._rates:
            return None

        # 前後30日以内で最も近い日付を探す
        date_range = 30
        closest_date = None
        min_diff = timedelta(days=date_range)

        start_date = target_date - timedelta(days=date_range)
        end_date = target_date + timedelta(days=date_range)

        for rate_date in self._rates.keys():
            if start_date <= rate_date <= end_date:
                diff = abs(rate_date - target_date)
                if diff < min_diff:
                    min_diff = diff
                    closest_date = rate_date

        return closest_date

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """日付文字列をパース"""
        try:
            # 様々な日付形式に対応
            for fmt in ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue
            raise ValueError(f"Unsupported date format: {date_str}")
        except Exception as e:
            raise ValueError(f"Date parsing error: {e}")

class ExchangeRateCache:
    """為替レートのキャッシュ管理クラス"""
    
    def __init__(self, provider: ExchangeRateProvider, cache_duration: int = 30):
        self._provider = provider
        self._cache: Dict[date, Tuple[Decimal, datetime]] = {}
        self._cache_duration = timedelta(days=cache_duration)

    def get_rate(self, target_date: date) -> Decimal:
        """キャッシュを考慮して為替レートを取得"""
        self._clean_expired_cache()
        
        if target_date in self._cache:
            rate, _ = self._cache[target_date]
            return rate

        rate = self._provider.get_rate(target_date)
        self._cache[target_date] = (rate, datetime.now())
        return rate

    def _clean_expired_cache(self) -> None:
        """期限切れのキャッシュを削除"""
        now = datetime.now()
        expired_dates = [
            d for d, (_, timestamp) in self._cache.items()
            if now - timestamp > self._cache_duration
        ]
        for date_ in expired_dates:
            del self._cache[date_]

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self._cache.clear()
