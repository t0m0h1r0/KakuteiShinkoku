# core/parser.py

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from .error import ParseError
from .tx import Transaction

class TransactionParser:
    """トランザクションのパース処理を担当"""

    @staticmethod
    def parse_date(date_str: str) -> date:
        """日付文字列をパース"""
        formats = ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y', '%d/%m/%Y']
        
        if not date_str:
            raise ParseError("日付が空です")
        
        clean_date_str = date_str.split(' as of ')[0].strip()
        
        for fmt in formats:
            try:
                return datetime.strptime(clean_date_str, fmt).date()
            except ValueError:
                continue
        
        raise ParseError(f"日付のパースに失敗: {date_str}")

    @staticmethod
    def parse_amount(value: str) -> Decimal:
        """金額文字列をDecimalに変換"""
        if not value:
            return Decimal('0')
        
        try:
            cleaned = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            return Decimal('0')

    @staticmethod
    def parse_quantity(value: str) -> Optional[Decimal]:
        """数量のパース"""
        try:
            cleaned = value.replace(',', '').strip()
            return Decimal(cleaned) if cleaned else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def parse_price(value: str) -> Optional[Decimal]:
        """価格のパース"""
        try:
            cleaned = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned) if cleaned else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def parse_fees(value: str) -> Optional[Decimal]:
        """手数料のパース"""
        try:
            cleaned = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned) if cleaned else None
        except (InvalidOperation, ValueError):
            return None