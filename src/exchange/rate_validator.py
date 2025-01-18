from typing import Dict
from datetime import date
from decimal import Decimal
import logging

class ValidationResult:
    """バリデーション結果を表すクラス"""
    def __init__(self):
        self.is_valid = True
        self.warnings = []
        self.errors = []

    def add_warning(self, message: str) -> None:
        """警告を追加"""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """エラーを追加"""
        self.is_valid = False
        self.errors.append(message)

class RateValidator:
    """為替レートバリデータークラス"""
    
    def __init__(self, anomaly_threshold: Decimal = Decimal('30')):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.anomaly_threshold = anomaly_threshold

    def validate(self, rates: Dict[date, Decimal]) -> ValidationResult:
        """レートのバリデーション実行"""
        result = ValidationResult()

        if not rates:
            result.add_error("No exchange rates available")
            return result

        # 基本チェック
        self._validate_basic_requirements(rates, result)
        
        # 異常値チェック
        if result.is_valid:
            self._validate_rate_values(rates, result)

        return result

    def _validate_basic_requirements(self, rates: Dict[date, Decimal], result: ValidationResult) -> None:
        """基本要件のバリデーション"""
        # 日付の連続性チェック
        dates = sorted(rates.keys())
        for i in range(1, len(dates)):
            days_diff = (dates[i] - dates[i-1]).days
            if days_diff > 5:  # 5営業日以上の間隔があれば警告
                result.add_warning(
                    f"Gap in rates between {dates[i-1]} and {dates[i]}: {days_diff} days"
                )

        # レート値の基本チェック
        for date_, rate in rates.items():
            if rate <= Decimal('0'):
                result.add_error(f"Invalid negative or zero rate on {date_}: {rate}")

    def _validate_rate_values(self, rates: Dict[date, Decimal], result: ValidationResult) -> None:
        """レート値の異常値チェック"""
        values = list(rates.values())
        avg_rate = sum(values) / len(values)
        
        # 移動平均との比較
        window_size = 5
        for i in range(len(values) - window_size + 1):
            window = values[i:i+window_size]
            window_avg = sum(window) / len(window)
            current_rate = values[i+window_size-1]
            
            # 移動平均から大きく外れているかチェック
            if abs((current_rate - window_avg) / window_avg) > self.anomaly_threshold / 100:
                date_ = list(rates.keys())[i+window_size-1]
                result.add_warning(
                    f"Potentially anomalous rate on {date_}: {current_rate} "
                    f"(Moving average: {window_avg})"
                )

        # 全体の分布からの外れ値チェック
        for date_, rate in rates.items():
            if abs((rate - avg_rate) / avg_rate) > self.anomaly_threshold / 100:
                result.add_warning(
                    f"Rate significantly different from average on {date_}: {rate} "
                    f"(Average: {avg_rate})"
                )
