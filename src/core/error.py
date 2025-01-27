# core/error.py

from typing import Optional
from decimal import Decimal
from datetime import date

class InvestmentError(Exception):
    """投資処理の基本例外クラス"""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}

class DataError(InvestmentError):
    """データ処理関連の基本例外クラス"""
    pass

class LoaderError(DataError):
    """データ読み込み関連の例外"""
    def __init__(self, message: str, source: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.source = source

class ParseError(DataError):
    """データパース処理の例外"""
    def __init__(self, message: str, raw_value: str, target_type: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.raw_value = raw_value
        self.target_type = target_type

class ValidationError(DataError):
    """データバリデーション関連の例外"""
    pass

class TransactionError(InvestmentError):
    """トランザクション処理の例外"""
    def __init__(self, message: str, transaction_date: Optional[date] = None, 
                 symbol: Optional[str] = None, amount: Optional[Decimal] = None,
                 details: Optional[dict] = None):
        super().__init__(message, details)
        self.transaction_date = transaction_date
        self.symbol = symbol
        self.amount = amount

class PositionError(InvestmentError):
    """ポジション管理の例外"""
    def __init__(self, message: str, symbol: str, details: Optional[dict] = None):
        super().__init__(message, details)
        self.symbol = symbol

class ConfigurationError(InvestmentError):
    """設定関連の例外"""
    pass

class ExchangeRateError(InvestmentError):
    """為替レート関連の例外"""
    def __init__(self, message: str, base_currency: str, target_currency: str, 
                 rate_date: Optional[date] = None, details: Optional[dict] = None):
        super().__init__(message, details)
        self.base_currency = base_currency
        self.target_currency = target_currency
        self.rate_date = rate_date