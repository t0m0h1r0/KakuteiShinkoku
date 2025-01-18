from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal

from ..core.types.transaction import Transaction
from ..config.settings import INPUT_DATE_FORMAT

class TransactionLoader(ABC):
    """トランザクションローダーの基底クラス"""
    
    @abstractmethod
    def load(self, source: Path) -> List[Transaction]:
        """指定されたソースからトランザクションを読み込む"""
        pass

class JSONTransactionLoader(TransactionLoader):
    """JSONファイルからトランザクションを読み込むクラス"""
    
    def load(self, source: Path) -> List[Transaction]:
        """JSONファイルからトランザクションを読み込む"""
        import json
        import logging
        
        logger = logging.getLogger(self.__class__.__name__)
        
        try:
            with source.open('r', encoding='utf-8') as f:
                data = json.load(f)
                transactions = []
                
                for trans in data.get('BrokerageTransactions', []):
                    try:
                        transaction = Transaction(
                            transaction_date=self._parse_date(trans['Date']),
                            account_id=source.stem,
                            symbol=trans.get('Symbol', ''),
                            description=trans['Description'],
                            amount=self._parse_amount(trans['Amount']),
                            action_type=trans['Action'],
                            quantity=self._parse_amount(trans.get('Quantity', '0')),
                            price=self._parse_amount(trans.get('Price', '0')),
                            fees=self._parse_amount(trans.get('Fees & Comm', '0'))
                        )
                        transactions.append(transaction)
                    except Exception as trans_error:
                        logger.warning(f"Error processing transaction: {trans_error}")
                
                return transactions
        
        except Exception as e:
            logger.error(f"Error loading transactions from {source}: {e}")
            return []

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """日付文字列をパース"""
        # 様々な形式の日付文字列に対応
        # 1. 'as of' が含まれる場合は分割
        # 2. 余分な空白や文字を除去
        clean_date_str = date_str.split(' as of ')[0].strip()
        
        # 対応する日付形式のリスト
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
        
        # どの形式にも一致しない場合
        raise ValueError(f"日付のパースに失敗しました: {date_str}")

    @staticmethod
    def _parse_amount(value: str) -> Decimal:
        """金額文字列をDecimalに変換"""
        if not value or value == '':
            return Decimal('0')
        
        # '$'や','を削除してから変換
        try:
            return Decimal(value.replace('$', '').replace(',', '').strip())
        except (ValueError, TypeError):
            return Decimal('0')
