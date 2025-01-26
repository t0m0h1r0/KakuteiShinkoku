# core/loader.py

from abc import ABC, abstractmethod
from typing import List, Optional
from pathlib import Path
import json
import logging

from .error import LoaderError
from .tx import Transaction
from .parser import TransactionParser

class Loader(ABC):
    """データローダーの基底クラス"""
    
    @abstractmethod
    def load(self, source: Path) -> List[Transaction]:
        """指定されたソースからデータを読み込む"""
        pass

class JSONLoader(Loader):
    """JSONファイルからトランザクションを読み込む"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parser = TransactionParser()

    def load(self, source: Path) -> List[Transaction]:
        """JSONファイルを読み込んでトランザクションのリストを返す"""
        try:
            with source.open('r', encoding='utf-8') as f:
                data = json.load(f)
            return self._process_transactions(data, source.stem)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONデコードエラー: {source} - {e}")
            raise LoaderError(f"JSONデコードに失敗: {e}")
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {source} - {e}")
            raise LoaderError(f"ファイル読み込みに失敗: {e}")

    def _process_transactions(self, data: dict, account_id: str) -> List[Transaction]:
        """JSONデータからトランザクションを生成"""
        transactions = []
        
        for record in data.get('BrokerageTransactions', []):
            try:
                transaction = self._create_transaction(record, account_id)
                transactions.append(transaction)
            except Exception as e:
                self.logger.warning(f"トランザクション処理をスキップ: {e}")
                continue
                
        return transactions

    def _create_transaction(self, record: dict, account_id: str) -> Transaction:
        """トランザクションオブジェクトを生成"""
        return Transaction(
            transaction_date=self.parser.parse_date(record.get('Date', '')),
            account_id=account_id,
            symbol=record.get('Symbol', ''),
            description=record.get('Description', ''),
            amount=self.parser.parse_amount(record.get('Amount', '')),
            action_type=record.get('Action', ''),
            quantity=self.parser.parse_quantity(record.get('Quantity', '')),
            price=self.parser.parse_price(record.get('Price', '')),
            fees=self.parser.parse_fees(record.get('Fees & Comm', ''))
        )