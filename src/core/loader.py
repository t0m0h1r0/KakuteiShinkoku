# core/loader.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
import logging
from datetime import datetime
from decimal import Decimal

from .error import LoaderError
from .tx import Transaction
from .parser import TransactionParser

class BaseLoader(ABC):
    """データローダーの基底クラス"""
    
    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load(self, source: Path) -> List[Transaction]:
        """
        データソースからトランザクションを読み込む
        
        Args:
            source (Path): データソースのパス
            
        Returns:
            List[Transaction]: 読み込んだトランザクションのリスト
            
        Raises:
            LoaderError: 読み込みに失敗した場合
        """
        pass

class JSONLoader(BaseLoader):
    """JSONファイルからトランザクションを読み込むローダー"""

    def __init__(self) -> None:
        super().__init__()
        self.parser = TransactionParser()

    def load(self, source: Path) -> List[Transaction]:
        """
        JSONファイルからトランザクションを読み込む
        
        Args:
            source (Path): JSONファイルのパス
            
        Returns:
            List[Transaction]: トランザクションのリスト
            
        Raises:
            LoaderError: 読み込みに失敗した場合
        """
        try:
            transactions = self._load_json_file(source)
            return self._process_transactions(transactions, source.stem)
        except LoaderError:
            raise
        except Exception as e:
            self.logger.error(f"ファイル読み込みエラー: {source} - {e}")
            raise LoaderError(f"ファイル読み込みに失敗: {e}")

    def _load_json_file(self, file_path: Path) -> Dict[str, Any]:
        """
        JSONファイルを読み込む
        
        Args:
            file_path (Path): JSONファイルのパス
            
        Returns:
            Dict[str, Any]: 読み込んだJSONデータ
            
        Raises:
            LoaderError: 読み込みに失敗した場合
        """
        try:
            with file_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                
            self._validate_json_structure(data)
            return data
            
        except json.JSONDecodeError as e:
            error_msg = f"JSONデコードエラー: {file_path} - {e}"
            self.logger.error(error_msg)
            raise LoaderError(error_msg)
        except Exception as e:
            error_msg = f"ファイル読み込みエラー: {file_path} - {e}"
            self.logger.error(error_msg)
            raise LoaderError(error_msg)

    def _validate_json_structure(self, data: Dict[str, Any]) -> None:
        """
        JSONデータの構造を検証
        
        Args:
            data (Dict[str, Any]): 検証対象のJSONデータ
            
        Raises:
            LoaderError: 検証に失敗した場合
        """
        required_fields = {'FromDate', 'ToDate', 'BrokerageTransactions'}
        
        if not all(field in data for field in required_fields):
            missing_fields = required_fields - set(data.keys())
            raise LoaderError(f"必須フィールドがありません: {missing_fields}")
            
        if not isinstance(data['BrokerageTransactions'], list):
            raise LoaderError("BrokerageTransactionsはリストである必要があります")

    def _process_transactions(self, data: Dict[str, Any], account_id: str) -> List[Transaction]:
        """
        JSONデータからトランザクションを生成
        
        Args:
            data (Dict[str, Any]): JSONデータ
            account_id (str): アカウントID
            
        Returns:
            List[Transaction]: 生成したトランザクションのリスト
        """
        transactions = []
        
        for record in data.get('BrokerageTransactions', []):
            try:
                transaction = self._create_transaction(record, account_id)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                self.logger.warning(f"トランザクション処理をスキップ: {record.get('Date', '不明')} - {e}")
                continue

        self.logger.info(f"{len(transactions)}件のトランザクションを読み込みました")
        return transactions

    def _create_transaction(self, record: Dict[str, Any], account_id: str) -> Optional[Transaction]:
        """
        レコードからトランザクションを生成
        
        Args:
            record (Dict[str, Any]): トランザクションレコード
            account_id (str): アカウントID
            
        Returns:
            Optional[Transaction]: 生成したトランザクション
        """
        try:
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
        except Exception as e:
            self.logger.warning(f"トランザクション生成エラー: {e}")
            return None