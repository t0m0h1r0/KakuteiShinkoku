from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Type, TypeVar, cast
from pathlib import Path
import json
import logging
from datetime import datetime

from .error import LoaderError
from .tx import Transaction
from .parser import TransactionParser, ParserConfig

T = TypeVar('T')

class BaseLoader(ABC):
    """
    データローダーの基底クラス
    
    全てのローダーの基本機能を定義します。
    サブクラスは具体的なデータ読み込み処理を実装する必要があります。
    """
    
    def __init__(self) -> None:
        """ローダーを初期化"""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def load(self, source: Path) -> List[Any]:
        """
        データソースからデータを読み込む
        
        Args:
            source: データソースのパス
            
        Returns:
            読み込んだデータのリスト
            
        Raises:
            LoaderError: データ読み込み中のエラー
        """
        pass

    def _validate_source(self, source: Path) -> None:
        """
        データソースを検証
        
        Args:
            source: 検証するパス
            
        Raises:
            LoaderError: ソースが無効な場合
        """
        if not source.exists():
            raise LoaderError(
                f"ソースファイルが存在しません: {source}",
                str(source),
                {'type': 'file_not_found'}
            )
        if not source.is_file():
            raise LoaderError(
                f"指定されたパスはファイルではありません: {source}",
                str(source),
                {'type': 'invalid_source_type'}
            )

class JSONLoader(BaseLoader):
    """
    JSONファイルからトランザクションを読み込むローダー
    
    JSONファイルを解析し、Transactionオブジェクトのリストを生成します。
    日付範囲でのフィルタリングをサポートします。
    """
    
    def __init__(self, parser_config: Optional[ParserConfig] = None) -> None:
        """
        JSONローダーを初期化
        
        Args:
            parser_config: パーサーの設定（オプション）
        """
        super().__init__()
        self.parser = TransactionParser(parser_config)

    def load(self, source: Path) -> List[Transaction]:
        """
        JSONファイルからトランザクションを読み込む
        
        Args:
            source: JSONファイルのパス
            
        Returns:
            Transactionオブジェクトのリスト
            
        Raises:
            LoaderError: ファイル読み込みまたは解析エラー
        """
        try:
            self._validate_source(source)
            self.logger.debug(f"JSONファイルの読み込みを開始: {source}")
            
            with source.open('r', encoding='utf-8') as f:
                data = self._load_json(f)
                
            transactions = self._process_transactions(data, source.stem)
            self.logger.info(f"{len(transactions)}件のトランザクションを読み込みました: {source}")
            
            return transactions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONの解析に失敗: {e}")
            raise LoaderError(
                f"JSONファイルの解析に失敗: {source}",
                str(source),
                {'error': str(e), 'line': e.lineno, 'column': e.colno}
            )
        except Exception as e:
            self.logger.error(f"ファイル読み込み中にエラー: {e}")
            raise LoaderError(
                f"ファイルの読み込みに失敗: {source}",
                str(source),
                {'error': str(e)}
            )

    def _load_json(self, file) -> Dict[str, Any]:
        """
        JSONファイルを読み込んで解析
        
        Args:
            file: オープンされたファイルオブジェクト
            
        Returns:
            解析されたJSONデータ
            
        Raises:
            json.JSONDecodeError: JSON解析エラー
        """
        try:
            return json.load(file)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONの解析に失敗: {e}")
            raise

    def _process_transactions(self, data: Dict[str, Any], account_id: str) -> List[Transaction]:
        """
        JSONデータからトランザクションを生成
        
        Args:
            data: 解析されたJSONデータ
            account_id: アカウントID
            
        Returns:
            生成されたTransactionオブジェクトのリスト
        """
        transactions: List[Transaction] = []
        from_date = self._parse_date(data.get('FromDate'))
        to_date = self._parse_date(data.get('ToDate'))
        
        self.logger.debug(f"トランザクション処理: {from_date} から {to_date}")
        
        for record in data.get('BrokerageTransactions', []):
            try:
                record['account_id'] = account_id
                transaction = self.parser.parse_transaction(record)
                
                if self._validate_transaction_date(transaction, from_date, to_date):
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.warning(
                    f"トランザクションの処理をスキップ: {e}",
                    extra={'record': record}
                )
                continue
                
        return transactions

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        日付文字列をパース
        
        Args:
            date_str: パースする日付文字列
            
        Returns:
            パースされたdatetimeオブジェクト、またはNone
        """
        if not date_str:
            return None
            
        try:
            return datetime.strptime(date_str, '%m/%d/%Y')
        except ValueError:
            self.logger.warning(f"日付のパースに失敗: {date_str}")
            return None

    def _validate_transaction_date(
        self, 
        transaction: Transaction,
        from_date: Optional[datetime],
        to_date: Optional[datetime]
    ) -> bool:
        """
        トランザクション日付が指定された範囲内かを検証
        
        Args:
            transaction: 検証するトランザクション
            from_date: 開始日（オプション）
            to_date: 終了日（オプション）
            
        Returns:
            日付が範囲内の場合True
        """
        if not from_date or not to_date:
            return True
            
        transaction_date = datetime.combine(
            transaction.transaction_date,
            datetime.min.time()
        )
        return from_date <= transaction_date <= to_date