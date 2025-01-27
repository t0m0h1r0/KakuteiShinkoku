# core/parser.py

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, Any, Callable
import re
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .error import ParseError
from .tx import Transaction

@dataclass(frozen=True)
class ParserConfig:
    """パーサーの設定値を保持する不変クラス"""
    
    # 日付フォーマットのパターン
    DATE_FORMATS = [
        '%m/%d/%Y',
        '%Y-%m-%d',
        '%m/%d/%y',
        '%d/%m/%Y'
    ]
    
    # 数値のクリーンアップパターン
    NUMERIC_CLEANUP_PATTERNS = {
        'amount': r'[^-0-9.]',
        'quantity': r'[^-0-9.]',
        'price': r'[^-0-9.]',
        'fees': r'[^-0-9.]'
    }
    
    # アクションタイプの正規化マッピング
    ACTION_TYPE_MAPPING = {
        'BOUGHT': 'BUY',
        'PURCHASED': 'BUY',
        'SOLD': 'SELL',
        'DIVIDEND': 'DIVIDEND',
        'DIV': 'DIVIDEND',
        'INTEREST': 'INTEREST',
        'INT': 'INTEREST'
    }

class BaseParser(ABC):
    """パーサーの基底クラス"""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cleanup_patterns = {
            field: re.compile(pattern)
            for field, pattern in ParserConfig.NUMERIC_CLEANUP_PATTERNS.items()
        }

    @abstractmethod
    def parse(self, value: Any) -> Any:
        """値をパースする抽象メソッド"""
        pass

    def _clean_numeric(self, value: str, field: str) -> str:
        """数値文字列のクリーンアップ"""
        if not value:
            return '0'
        pattern = self._cleanup_patterns.get(field)
        if not pattern:
            return value.strip()
        return pattern.sub('', value.strip())

class DateParser(BaseParser):
    """日付パーサー"""
    
    def parse(self, date_str: str) -> date:
        """
        日付文字列をパース
        
        Args:
            date_str (str): パース対象の日付文字列
            
        Returns:
            date: パース結果の日付オブジェクト
            
        Raises:
            ParseError: パースに失敗した場合
        """
        if not date_str:
            raise ParseError("日付が空です")
        
        # 'as of' を含む場合は前半部分のみを使用
        clean_date_str = date_str.split(' as of ')[0].strip()
        
        for fmt in ParserConfig.DATE_FORMATS:
            try:
                return datetime.strptime(clean_date_str, fmt).date()
            except ValueError:
                continue
        
        raise ParseError(f"日付のパースに失敗: {date_str}")

class DecimalParser(BaseParser):
    """Decimal型パーサー"""
    
    def parse(self, value: str, field: str = 'amount') -> Optional[Decimal]:
        """
        数値文字列をDecimalにパース
        
        Args:
            value (str): パース対象の数値文字列
            field (str): フィールド名（デフォルト: 'amount'）
            
        Returns:
            Optional[Decimal]: パース結果のDecimal値
        """
        if not value:
            return None
            
        try:
            cleaned = self._clean_numeric(value, field)
            return Decimal(cleaned) if cleaned else None
        except (InvalidOperation, ValueError):
            self.logger.debug(f"数値パースに失敗: {value}")
            return None

class TransactionParser:
    """トランザクションパーサー"""
    
    def __init__(self) -> None:
        self._date_parser = DateParser()
        self._decimal_parser = DecimalParser()
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse_date(self, date_str: str) -> date:
        """日付のパース"""
        return self._date_parser.parse(date_str)

    def parse_amount(self, value: str) -> Decimal:
        """金額のパース"""
        return self._decimal_parser.parse(value, 'amount') or Decimal('0')

    def parse_quantity(self, value: str) -> Optional[Decimal]:
        """数量のパース"""
        return self._decimal_parser.parse(value, 'quantity')

    def parse_price(self, value: str) -> Optional[Decimal]:
        """価格のパース"""
        return self._decimal_parser.parse(value, 'price')

    def parse_fees(self, value: str) -> Optional[Decimal]:
        """手数料のパース"""
        return self._decimal_parser.parse(value, 'fees')

    def normalize_action_type(self, action: str) -> str:
        """
        アクションタイプの正規化
        
        Args:
            action (str): 正規化対象のアクション文字列
            
        Returns:
            str: 正規化されたアクション文字列
        """
        normalized = action.upper().strip()
        return ParserConfig.ACTION_TYPE_MAPPING.get(normalized, normalized)