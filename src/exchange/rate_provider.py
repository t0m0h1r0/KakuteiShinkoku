from pathlib import Path
from typing import Dict, Optional
from datetime import date, timedelta
from decimal import Decimal
import logging

from ..core.interfaces import IExchangeRateProvider
from ..config.settings import DEFAULT_EXCHANGE_RATE
from .rate_loader import RateLoader, RateLoadError
from .rate_validator import RateValidator, ValidationResult

class RateProviderError(Exception):
    """為替レートプロバイダーのエラー"""
    pass

class RateProvider(IExchangeRateProvider):
    """為替レートプロバイダー"""
    
    def __init__(self, rate_file: Path, loader: RateLoader, validator: RateValidator):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rate_file = rate_file
        self._loader = loader
        self._validator = validator
        self._rates: Dict[date, Decimal] = {}
        self._validation_result: Optional[ValidationResult] = None
        
        self._initialize_rates()

    def get_rate(self, target_date: date) -> Decimal:
        """指定日の為替レートを取得"""
        try:
            if target_date in self._rates:
                return self._rates[target_date]

            closest_date = self._find_closest_date(target_date)
            if closest_date:
                self.logger.info(
                    f"Using closest available rate from {closest_date} "
                    f"for requested date {target_date}"
                )
                return self._rates[closest_date]
            
            self.logger.warning(
                f"No rate found for {target_date}, using default rate"
            )
            return DEFAULT_EXCHANGE_RATE

        except Exception as e:
            self.logger.error(f"Error getting rate for {target_date}: {e}")
            return DEFAULT_EXCHANGE_RATE

    def get_validation_warnings(self) -> list:
        """バリデーション警告を取得"""
        return self._validation_result.warnings if self._validation_result else []

    def get_validation_errors(self) -> list:
        """バリデーションエラーを取得"""
        return self._validation_result.errors if self._validation_result else []

    def _initialize_rates(self) -> None:
        """レートの初期化"""
        try:
            # レートの読み込み
            self._rates = self._loader.load_rates(self._rate_file)
            
            # バリデーション実行
            self._validation_result = self._validator.validate(self._rates)
            
            # バリデーション結果のログ出力
            self._log_validation_results()
            
        except RateLoadError as e:
            self.logger.error(f"Failed to initialize rates: {e}")
            self._rates = {}
            raise RateProviderError(f"Rate initialization failed: {e}")

    def _log_validation_results(self) -> None:
        """バリデーション結果をログに出力"""
        if not self._validation_result:
            return

        for warning in self._validation_result.warnings:
            self.logger.warning(f"Rate validation warning: {warning}")

        for error in self._validation_result.errors:
            self.logger.error(f"Rate validation error: {error}")

    def _find_closest_date(self, target_date: date) -> Optional[date]:
        """指定日に最も近い日付を探す"""
        if not self._rates:
            return None

        date_range = 30  # 前後30日以内で探す
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

    def refresh_rates(self) -> None:
        """レートを再読み込み"""
        self._initialize_rates()