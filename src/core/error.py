# core/error.py

class TransactionError(Exception):
    """トランザクション処理の基本例外クラス"""
    pass

class LoaderError(TransactionError):
    """ローダー関連の例外"""
    pass

class ParseError(TransactionError):
    """パース処理の例外"""
    pass

class ValidationError(TransactionError):
    """バリデーション関連の例外"""
    pass