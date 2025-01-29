from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import date


class InvestmentError(Exception):
    """
    投資処理の基本例外クラス

    アプリケーション固有の全ての例外の基底クラスとして機能し、
    エラーの詳細情報を構造化された形で保持します。
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message)
        self.details = details or {}


class DataError(InvestmentError):
    """
    データ処理関連の基本例外クラス

    データの読み込み、パース、検証に関する
    全ての例外の基底クラスとして機能します。
    """

    pass


class LoaderError(DataError):
    """
    データ読み込み関連の例外

    ファイルの読み込みやデータソースへのアクセスに
    関するエラーを表現します。
    """

    def __init__(self, message: str, source: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            source: エラーが発生したデータソース
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message, details)
        self.source = source


class ParseError(DataError):
    """
    データパース処理の例外

    データの解析や型変換に関するエラーを
    表現します。
    """

    def __init__(self, message: str, raw_value: str, target_type: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            raw_value: パースに失敗した元の値
            target_type: 変換しようとした目標の型
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message, details)
        self.raw_value = raw_value
        self.target_type = target_type


class ValidationError(DataError):
    """
    データバリデーション関連の例外

    データの検証に失敗した場合に発生する
    エラーを表現します。
    """

    pass


class TransactionError(InvestmentError):
    """
    トランザクション処理の例外

    取引データの処理中に発生するエラーを
    表現します。
    """

    def __init__(
        self,
        message: str,
        transaction_date: Optional[date] = None,
        symbol: Optional[str] = None,
        amount: Optional[Decimal] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            transaction_date: エラーが発生した取引の日付
            symbol: エラーが発生した銘柄シンボル
            amount: エラーが発生した取引金額
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message, details)
        self.transaction_date = transaction_date
        self.symbol = symbol
        self.amount = amount


class PositionError(InvestmentError):
    """
    ポジション管理の例外

    ポジション計算や更新時に発生するエラーを
    表現します。
    """

    def __init__(self, message: str, symbol: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            symbol: エラーが発生した銘柄シンボル
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message, details)
        self.symbol = symbol


class ConfigurationError(InvestmentError):
    """
    設定関連の例外

    設定の読み込みや検証時に発生するエラーを
    表現します。
    """

    pass


class ExchangeRateError(InvestmentError):
    """
    為替レート関連の例外

    為替レートの取得や計算時に発生するエラーを
    表現します。
    """

    def __init__(
        self,
        message: str,
        base_currency: str,
        target_currency: str,
        rate_date: Optional[date] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        例外を初期化

        Args:
            message: エラーメッセージ
            base_currency: 基準通貨
            target_currency: 変換先通貨
            rate_date: レート参照日
            details: エラーの詳細情報（オプション）
        """
        super().__init__(message, details)
        self.base_currency = base_currency
        self.target_currency = target_currency
        self.rate_date = rate_date

    def __str__(self) -> str:
        """エラーの文字列表現を返す"""
        base_info = f"{self.base_currency}/{self.target_currency}"
        date_info = f" ({self.rate_date})" if self.rate_date else ""
        return f"{super().__str__()} [{base_info}{date_info}]"