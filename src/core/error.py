"""
エラー定義モジュール

このモジュールは、アプリケーション全体で使用する
カスタムエラークラスを定義します。
"""

class TransactionError(Exception):
    """取引処理の基本例外クラス
    
    全ての取引関連エラーの基底クラスとなります。
    
    Attributes:
        message: エラーメッセージ
        details: 追加の詳細情報（オプション）
    """
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class LoaderError(TransactionError):
    """データ読み込み関連のエラー
    
    ファイルの読み込みやパースに失敗した場合に発生します。
    """
    pass

class ParseError(TransactionError):
    """パース処理のエラー
    
    データの解析や変換に失敗した場合に発生します。
    """
    pass

class ValidationError(TransactionError):
    """バリデーション関連のエラー
    
    データの検証に失敗した場合に発生します。
    """
    pass

class ProcessingError(TransactionError):
    """取引処理中のエラー
    
    取引の処理中に発生する様々なエラーを扱います。
    
    Examples:
        >>> try:
        ...     raise ProcessingError("無効な取引", {"symbol": "AAPL"})
        ... except ProcessingError as e:
        ...     print(f"エラー: {e.message}, 詳細: {e.details}")
    """
    pass

class PositionError(TransactionError):
    """ポジション管理のエラー
    
    ポジションの更新や計算に失敗した場合に発生します。
    """
    pass

class ConfigurationError(TransactionError):
    """設定関連のエラー
    
    設定の読み込みや検証に失敗した場合に発生します。
    """
    pass

class ExchangeRateError(TransactionError):
    """為替レート関連のエラー
    
    為替レートの取得や計算に失敗した場合に発生します。
    """
    pass