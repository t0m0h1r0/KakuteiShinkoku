from abc import ABC, abstractmethod
from typing import List, Optional, Union
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import json
import logging

from ..core.transaction import Transaction

class TransactionParseError(Exception):
    """トランザクションのパース中に発生する例外"""
    pass

class TransactionLoader(ABC):
    """トランザクションローダーの基底クラス"""
    
    @abstractmethod
    def load(self, source: Path) -> List[Transaction]:
        """指定されたソースからトランザクションを読み込む"""
        pass

class JSONTransactionLoader(TransactionLoader):
    """JSONファイルからトランザクションを読み込むクラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """ロガーの初期化"""
        self.logger = logger or logging.getLogger(self.__class__.__name__)

    def load(self, source: Path) -> List[Transaction]:
        """JSONファイルからトランザクションを読み込む"""
        try:
            return self._load_transactions(source)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSONデコードエラー: {source} - {e}")
            return []
        except Exception as e:
            self.logger.error(f"トランザクション読み込み中にエラーが発生: {source} - {e}")
            return []

    def _load_transactions(self, source: Path) -> List[Transaction]:
        """トランザクションの詳細な読み込み処理"""
        with source.open('r', encoding='utf-8') as f:
            data = json.load(f)
            transactions = []
            
            for trans in data.get('BrokerageTransactions', []):
                try:
                    transaction = self._create_transaction(trans, source.stem)
                    transactions.append(transaction)
                except TransactionParseError as e:
                    self.logger.warning(f"トランザクションのパースに失敗: {e}")
                except Exception as trans_error:
                    self.logger.error(f"トランザクション処理中の予期せぬエラー: {trans_error}")
            
            return transactions

    def _create_transaction(self, trans: dict, account_id: str) -> Transaction:
        """トランザクション生成の詳細メソッド"""
        try:
            return Transaction(
                transaction_date=self._parse_date(trans.get('Date', '')),
                account_id=account_id,
                symbol=trans.get('Symbol', ''),
                description=trans.get('Description', ''),
                amount=self._parse_amount(trans.get('Amount', '')),
                action_type=trans.get('Action', ''),
                quantity=self._parse_quantity(trans.get('Quantity', '')),
                price=self._parse_price(trans.get('Price', '')),
                fees=self._parse_fees(trans.get('Fees & Comm', ''))
            )
        except ValueError as e:
            raise TransactionParseError(f"トランザクションの生成に失敗: {e}")

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """日付文字列をパース（既存のロジックを改善）"""
        if not date_str:
            raise ValueError("日付が空です")
        
        # 'as of' が含まれる場合は分割
        clean_date_str = date_str.split(' as of ')[0].strip()
        
        date_formats = [
            '%m/%d/%Y',   # 米国形式 (12/31/2024)
            '%Y-%m-%d',   # ISO形式 (2024-12-31)
            '%m/%d/%y',   # 短縮年の米国形式 (12/31/24)
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(clean_date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"日付のパースに失敗しました: {date_str}")

    @staticmethod
    def _parse_amount(value: str) -> Decimal:
        """金額文字列をDecimalに変換（より堅牢な変換）"""
        if not value or value == '':
            return Decimal('0')
        
        try:
            # '$'や','を削除し、文字列の前後の空白も除去
            cleaned_value = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned_value)
        except (InvalidOperation, ValueError, TypeError):
            return Decimal('0')

    @staticmethod
    def _parse_quantity(value: str) -> Optional[Decimal]:
        """数量のパース"""
        try:
            cleaned_value = value.replace(',', '').strip()
            return Decimal(cleaned_value) if cleaned_value else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_price(value: str) -> Optional[Decimal]:
        """価格のパース"""
        try:
            cleaned_value = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned_value) if cleaned_value else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_fees(value: str) -> Optional[Decimal]:
        """手数料のパース"""
        try:
            cleaned_value = value.replace('$', '').replace(',', '').strip()
            return Decimal(cleaned_value) if cleaned_value else None
        except (InvalidOperation, ValueError):
            return None