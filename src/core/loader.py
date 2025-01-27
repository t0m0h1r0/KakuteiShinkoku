# core/loader.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type, TypeVar
from pathlib import Path
import json
import logging
from datetime import datetime

from .error import LoaderError
from .tx import Transaction
from .parser import TransactionParser, ParserConfig

T = TypeVar('T')

class BaseLoader(ABC):
    """データローダーの基底クラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load(self, source: Path) -> List[Any]:
        """データソースからデータを読み込む"""
        pass

    def _validate_source(self, source: Path) -> None:
        """データソースの検証"""
        if not source.exists():
            raise LoaderError(
                f"ソースが存在しません: {source}",
                str(source),
                {'type': 'file_not_found'}
            )
        if not source.is_file():
            raise LoaderError(
                f"ソースがファイルではありません: {source}",
                str(source),
                {'type': 'invalid_source_type'}
            )

class JSONLoader(BaseLoader):
    """JSONファイルからトランザクションを読み込む"""
    
    def __init__(self, parser_config: Optional[ParserConfig] = None):
        super().__init__()
        self.parser = TransactionParser(parser_config)

    def load(self, source: Path) -> List[Transaction]:
        """JSONファイルを読み込んでトランザクションのリストを返す"""
        try:
            self._validate_source(source)
            
            with source.open('r', encoding='utf-8') as f:
                data = self._load_json(f)
                
            return self._process_transactions(data, source.stem)
            
        except json.JSONDecodeError as e:
            raise LoaderError(
                f"JSONデコードエラー: {source}",
                str(source),
                {'error': str(e), 'line': e.lineno, 'column': e.colno}
            )
        except Exception as e:
            raise LoaderError(
                f"ファイル読み込みエラー: {source}",
                str(source),
                {'error': str(e)}
            )

    def _load_json(self, file) -> Dict[str, Any]:
        """JSONファイルの読み込み"""
        try:
            return json.load(file)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONの解析に失敗: {e}")
            raise

    def _process_transactions(self, data: Dict[str, Any], account_id: str) -> List[Transaction]:
        """JSONデータからトランザクションを生成"""
        transactions = []
        from_date = self._parse_date(data.get('FromDate'))
        to_date = self._parse_date(data.get('ToDate'))
        
        for record in data.get('BrokerageTransactions', []):
            try:
                # アカウントIDの追加
                record['account_id'] = account_id
                transaction = self.parser.parse_transaction(record)
                
                # 日付範囲のバリデーション
                if self._validate_transaction_date(transaction, from_date, to_date):
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.warning(
                    f"トランザクション処理をスキップ: {e}",
                    extra={'record': record}
                )
                continue
                
        return transactions

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """日付文字列のパース"""
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            self.logger.warning(f"日付のパースに失敗: {date_str}")
            return None

    def _validate_transaction_date(self, 
                                 transaction: Transaction,
                                 from_date: Optional[datetime],
                                 to_date: Optional[datetime]) -> bool:
        """取引日付の検証"""
        if not from_date or not to_date:
            return True
            
        transaction_date = datetime.combine(
            transaction.transaction_date,
            datetime.min.time()
        )
        return from_date <= transaction_date <= to_date