from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, Any, Dict, Type, TypeVar, List
import logging
from dataclasses import dataclass, field

from .error import ParseError
from .tx import Transaction

T = TypeVar('T')

@dataclass
class ParserConfig:
    """パーサーの設定を管理するデータクラス"""
    
    # 日付フォーマットのリスト
    date_formats: List[str] = field(default_factory=lambda: [
        '%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y', '%d/%m/%Y'
    ])
    
    # 数値フォーマットの設定
    decimal_separator: str = '.'
    thousand_separator: str = ','
    
    # 通貨記号のリスト
    currency_symbols: List[str] = field(default_factory=lambda: [
        '$', '¥', '€', '£'
    ])

class BaseParser:
    """
    基本パーサークラス
    
    数値や日付などの基本的なパース機能を提供します。
    サブクラスはこのクラスを継承して具体的なパース処理を実装します。
    """
    
    def __init__(self, config: Optional[ParserConfig] = None) -> None:
        """
        パーサーを初期化
        
        Args:
            config: パーサーの設定（オプション）
        """
        self.config = config or ParserConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _clean_numeric(self, value: str) -> str:
        """
        数値文字列をクリーニング
        
        Args:
            value: クリーニングする文字列
            
        Returns:
            クリーニングされた文字列
        """
        if not value:
            return '0'
        
        # 通貨記号の除去
        for symbol in self.config.currency_symbols:
            value = value.replace(symbol, '')
        
        # 桁区切りの除去と小数点の正規化
        value = value.replace(self.config.thousand_separator, '')
        return value.strip()

    def _parse_to_type(
        self, 
        value: Any, 
        target_type: Type[T], 
        field_name: str
    ) -> Optional[T]:
        """
        指定された型へ値をパース
        
        Args:
            value: パースする値
            target_type: 目標の型
            field_name: フィールド名（エラーメッセージ用）
            
        Returns:
            パースされた値、または None
            
        Raises:
            ParseError: パース失敗時
        """
        if value is None or value == '':
            return None
            
        try:
            if target_type is bool:
                return bool(value)
            return target_type(value)
        except (ValueError, TypeError) as e:
            raise ParseError(
                f"値のパースに失敗: {value} -> {target_type.__name__}",
                str(value),
                target_type.__name__,
                {'field': field_name, 'error': str(e)}
            )

class TransactionParser(BaseParser):
    """
    トランザクションパーサー
    
    トランザクションデータを解析し、Transactionオブジェクトを生成します。
    日付、金額、数量などの各フィールドの適切なパースを担当します。
    """

    def parse_date(self, date_str: str) -> date:
        """
        日付文字列をパース
        
        Args:
            date_str: パースする日付文字列
            
        Returns:
            パースされた日付オブジェクト
            
        Raises:
            ParseError: パース失敗時
        """
        if not date_str:
            raise ParseError("日付が空です", date_str, "date")
        
        # 'as of' の処理
        clean_date_str = date_str.split(' as of ')[0].strip()
        
        for fmt in self.config.date_formats:
            try:
                return datetime.strptime(clean_date_str, fmt).date()
            except ValueError:
                continue
        
        raise ParseError(
            f"日付のパースに失敗: {date_str}",
            date_str,
            "date",
            {'attempted_formats': self.config.date_formats}
        )

    def parse_amount(self, value: str) -> Decimal:
        """
        金額文字列をDecimalに変換
        
        Args:
            value: パースする金額文字列
            
        Returns:
            パースされたDecimal
            
        Raises:
            ParseError: パース失敗時
        """
        try:
            cleaned = self._clean_numeric(value)
            return Decimal(cleaned) if cleaned else Decimal('0')
        except InvalidOperation as e:
            raise ParseError(
                f"金額のパースに失敗: {value}",
                value,
                "decimal",
                {'error': str(e)}
            )

    def parse_quantity(self, value: str) -> Optional[Decimal]:
        """
        数量をパース
        
        Args:
            value: パースする数量文字列
            
        Returns:
            パースされたDecimal、または None
        """
        if not value:
            return None
            
        try:
            cleaned = self._clean_numeric(value)
            return Decimal(cleaned) if cleaned else None
        except InvalidOperation as e:
            raise ParseError(
                f"数量のパースに失敗: {value}",
                value,
                "decimal",
                {'error': str(e)}
            )

    def parse_price(self, value: str) -> Optional[Decimal]:
        """
        価格をパース
        
        Args:
            value: パースする価格文字列
            
        Returns:
            パースされたDecimal、または None
        """
        if not value:
            return None
            
        try:
            cleaned = self._clean_numeric(value)
            return Decimal(cleaned) if cleaned else None
        except InvalidOperation as e:
            raise ParseError(
                f"価格のパースに失敗: {value}",
                value,
                "decimal",
                {'error': str(e)}
            )

    def parse_fees(self, value: str) -> Optional[Decimal]:
        """
        手数料をパース
        
        Args:
            value: パースする手数料文字列
            
        Returns:
            パースされたDecimal、または None
        """
        if not value:
            return None
            
        try:
            cleaned = self._clean_numeric(value)
            return Decimal(cleaned) if cleaned else None
        except InvalidOperation as e:
            raise ParseError(
                f"手数料のパースに失敗: {value}",
                value,
                "decimal",
                {'error': str(e)}
            )

    def parse_transaction(self, data: Dict[str, Any]) -> Transaction:
        """
        トランザクションデータをパース
        
        Args:
            data: パースするトランザクションデータ
            
        Returns:
            パースされたTransactionオブジェクト
            
        Raises:
            ParseError: パース失敗時
        """
        try:
            return Transaction(
                transaction_date=self.parse_date(data.get('Date', '')),
                account_id=str(data.get('account_id', '')),
                symbol=str(data.get('Symbol', '')),
                description=str(data.get('Description', '')),
                amount=self.parse_amount(data.get('Amount', '')),
                action_type=str(data.get('Action', '')),
                quantity=self.parse_quantity(data.get('Quantity', '')),
                price=self.parse_price(data.get('Price', '')),
                fees=self.parse_fees(data.get('Fees & Comm', '')),
                metadata={'raw_data': data}
            )
        except ParseError:
            raise
        except Exception as e:
            raise ParseError(
                "トランザクションのパースに失敗",
                str(data),
                "transaction",
                {'error': str(e)}
            )