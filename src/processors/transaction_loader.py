from decimal import Decimal
from pathlib import Path
from typing import List
import json
import logging
from datetime import datetime

from src.core.interfaces import ITransactionLoader
from src.core.models import Transaction
from src.config.settings import (
    FILE_ENCODING, INPUT_DATE_FORMAT, OUTPUT_DATE_FORMAT
)

class JSONTransactionLoader(ITransactionLoader):
    """JSONファイルからトランザクションを読み込むクラス"""

    def __init__(self):
        self._logger = logging.getLogger(self.__class__.__name__)

    def load(self, source: str) -> List[Transaction]:
        """JSONファイルからトランザクションを読み込む"""
        try:
            path = Path(source)
            with path.open('r', encoding=FILE_ENCODING) as f:
                data = json.load(f)
                return [
                    self._create_transaction(trans, path.stem)
                    for trans in data['BrokerageTransactions']
                ]
        except Exception as e:
            self._logger.error(f"Error loading transactions from {source}: {e}")
            return []

    def _create_transaction(self, trans_data: dict, account: str) -> Transaction:
        """トランザクションデータからTransactionオブジェクトを作成"""
        date_str = self._parse_date(trans_data['Date'])
        try:
            # 入力形式で日付をパース
            transaction_date = datetime.strptime(date_str, INPUT_DATE_FORMAT).date()
            
            return Transaction(
                transaction_date=transaction_date,
                account_id=account,
                symbol=trans_data.get('Symbol', ''),
                description=trans_data['Description'],
                amount=self._parse_amount(trans_data['Amount']),
                action_type=trans_data['Action'],
                quantity=self._parse_amount(trans_data.get('Quantity', '')),
                price=self._parse_amount(trans_data.get('Price', '')),
                fees=self._parse_amount(trans_data.get('Fees & Comm', ''))
            )
        except ValueError as e:
            self._logger.error(f"Error parsing date '{date_str}': {e}")
            raise

    @staticmethod
    def _parse_date(date_str: str) -> str:
        """日付文字列をパース"""
        # 'as of' が含まれている場合は分割して最初の部分を使用
        parts = date_str.split(' as of ')
        return parts[0].strip()

    @staticmethod
    def _parse_amount(amount_str: str) -> Decimal:
        """金額文字列をDecimal型に変換"""
        if not amount_str or amount_str == '':
            return Decimal('0')
        return Decimal(amount_str.replace('$', '').replace(',', ''))