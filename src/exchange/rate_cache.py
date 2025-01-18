from typing import Dict, Tuple, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from functools import lru_cache

from ..core.interfaces import IExchangeRateProvider
from .rate_provider import RateProvider

class RateCache(IExchangeRateProvider):
    """為替レートキャッシュ"""
    
    def __init__(self, provider: RateProvider, cache_duration: int = 30, cache_size: int = 1000):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._provider = provider
        self._memory_cache: Dict[date, Tuple[Decimal, datetime]] = {}
        self._cache_duration = timedelta(days=cache_duration)
        self._lru_cache_size = cache_size

    def get_rate(self, target_date: date) -> Decimal:
        """キャッシュを考慮して為替レートを取得"""
        # まずメモリキャッシュをチェック
        rate = self._check_memory_cache(target_date)
        if rate is not None:
            return rate

        # LRUキャッシュをチェック
        rate = self._get_cached_rate(target_date)
        if rate is not None:
            self._update_memory_cache(target_date, rate)
            return rate

        # プロバイダーから取得
        rate = self._provider.get_rate(target_date)
        self._update_memory_cache(target_date, rate)
        return rate

    def _check_memory_cache(self, target_date: date) -> Optional[Decimal]:
        """メモリキャッシュをチェック"""
        self._clean_expired_cache()
        
        if target_date in self._memory_cache:
            rate, _ = self._memory_cache[target_date]
            self.logger.debug(f"Memory cache hit for {target_date}")
            return rate
        
        return None

    @lru_cache(maxsize=1000)
    def _get_cached_rate(self, target_date: date) -> Optional[Decimal]:
        """LRUキャッシュからレートを取得"""
        try:
            rate = self._provider.get_rate(target_date)
            self.logger.debug(f"LRU cache miss for {target_date}, fetched from provider")
            return rate
        except Exception as e:
            self.logger.error(f"Error fetching rate from provider: {e}")
            return None

    def _update_memory_cache(self, target_date: date, rate: Decimal) -> None:
        """メモリキャッシュを更新"""
        self._memory_cache[target_date] = (rate, datetime.now())

    def _clean_expired_cache(self) -> None:
        """期限切れのキャッシュを削除"""
        now = datetime.now()
        expired_dates = [
            d for d, (_, timestamp) in self._memory_cache.items()
            if now - timestamp > self._cache_duration
        ]
        for date_ in expired_dates:
            del self._memory_cache[date_]

    def clear_cache(self) -> None:
        """全てのキャッシュをクリア"""
        self._memory_cache.clear()
        self._get_cached_rate.cache_clear()

    def refresh(self) -> None:
        """キャッシュを更新"""
        self.clear_cache()
        self._provider.refresh_rates()