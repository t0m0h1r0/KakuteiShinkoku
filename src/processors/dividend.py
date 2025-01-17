from decimal import Decimal
from typing import Dict, Tuple, List
from datetime import datetime

from .base import BaseProcessor
from src.core.models import Transaction, DividendRecord, Money
from src.config.action_types import ActionTypes
from src.config.constants import Currency, IncomeType

class DividendProcessor(BaseProcessor[DividendRecord]):
    """配当処理クラス"""

    def __init__(self, exchange_rate_provider):
        super().__init__(exchange_rate_provider)
        self._dividend_records: Dict[Tuple[str, str, str], Dict] = {}

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """配当関連のトランザクションかどうかを判定"""
        return (ActionTypes.is_dividend_action(transaction.action_type) or
                ActionTypes.is_tax_action(transaction.action_type))

    def process_all(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """複数トランザクションの一括処理"""
        for transaction in transactions:
            try:
                self.process(transaction)
            except Exception as e:
                self._logger.error(f"Error processing transaction: {e}")
                continue
            
        # 全てのレコードを一度だけ追加
        self.records = [DividendRecord(**record) 
                       for record in self._dividend_records.values() 
                       if record['gross_amount'].amount > 0 or record['tax_amount'].amount > 0]
        return self.get_records()

    def _process_transaction(self, transaction: Transaction) -> None:
        """配当トランザクションを処理"""
        key = self._create_record_key(transaction)
        
        if key not in self._dividend_records:
            self._create_new_record(transaction, key)
        
        self._update_record(transaction, key)

    def _create_record_key(self, transaction: Transaction) -> Tuple[str, str, str]:
        """レコードのキーを生成"""
        return (
            transaction.transaction_date.isoformat(),
            transaction.symbol or transaction.description,
            transaction.account_id
        )

    def _create_new_record(self, transaction: Transaction, key: Tuple[str, str, str]) -> None:
        """新しい配当記録を作成"""
        self._dividend_records[key] = {
            'record_date': transaction.transaction_date,
            'account_id': transaction.account_id,
            'symbol': transaction.symbol,
            'description': transaction.description,
            'income_type': self._determine_income_type(transaction),
            'gross_amount': self._create_money(Decimal('0')),
            'tax_amount': self._create_money(Decimal('0')),
            'exchange_rate': self._get_exchange_rate(transaction.transaction_date),
            'is_reinvested': False,
            'principal_amount': self._create_money(Decimal('0'))
        }

    def _update_record(self, transaction: Transaction, key: Tuple[str, str, str]) -> None:
        """既存の配当記録を更新"""
        record = self._dividend_records[key]
        
        if ActionTypes.is_tax_action(transaction.action_type):
            record['tax_amount'] = self._create_money(abs(transaction.amount))
        else:
            record['gross_amount'] = self._create_money(transaction.amount)
            if transaction.action_type == 'REINVEST_DIVIDEND':
                record['is_reinvested'] = True

        # レコードをディクショナリに保持
        self._dividend_records[key] = record

    def _determine_income_type(self, transaction: Transaction) -> str:
        """収入タイプを判定"""
        if 'CD' in transaction.description:
            return IncomeType.CD_INTEREST
        elif 'INTEREST' in transaction.action_type:
            return IncomeType.INTEREST
        elif 'QUALIFIED' in transaction.action_type:
            return IncomeType.QUALIFIED_DIVIDEND
        else:
            return IncomeType.DIVIDEND