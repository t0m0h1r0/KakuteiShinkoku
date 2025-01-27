# core/parser.py

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, Any, Dict, Type, TypeVar
import re
import logging
from dataclasses import dataclass

from .error import ParseError
from .tx import Transaction

T = TypeVar('T')

@dataclass
class ParserConfig:
    """パーサーの設定"""
    date_formats: list[str] = None
    decimal_separator: str = '.'
    thousand_separator: str = ','
    currency_symbols: list[str] = None

    def __post_init__(self):
        """デフォルト値の設定"""
        if self.date_formats is None:
            self.date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y', '%d/%m/%Y']
        if self.currency_symbols is None:
            self.currency_symbols = ['$', '¥', '€', '£']

class BaseParser:
    """基本パーサークラス"""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _clean_numeric(self, value: str) -> str:
        """数値文字列のクリーニング"""
        if not value:
            return '0'
        
        # 通貨記号の除去
        for symbol in self.config.currency_symbols:
            value = value.replace(symbol, '')
        
        # 桁区切りの除去と小数点の正規化
        value = value.replace(self.config.thousand_separator, '')
        return value.strip()

    def _parse_to_type(self, value: Any, target_type: Type[T], field_name: str) -> Optional[T]:
        """指定された型へのパース"""
        if value is None or value == '':
            return None
            
        try:
            if target_type == bool:
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
    """トランザクションパーサー"""

    def parse_date(self, date_str: str) -> date:
        """日付文字列をパース"""
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
        """金額文字列をDecimalに変換"""
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
        """数量のパース"""
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
        """価格のパース"""
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
        """手数料のパース"""
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
        """トランザクションデータのパース"""
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
        except ParseError as e:
            raise
        except Exception as e:
            raise ParseError(
                f"トランザクションのパースに失敗",
                str(data),
                "transaction",
                {'error': str(e)}
            )