from decimal import Decimal
from typing import Dict, Tuple, List, Optional
from datetime import datetime, date

from .base import BaseProcessor
from src.core.models import Transaction, DividendRecord, Money
from src.config.action_types import ActionTypes
from src.config.constants import Currency, IncomeType

class DividendProcessor(BaseProcessor[DividendRecord]):
    def __init__(self, exchange_rate_provider):
        super().__init__(exchange_rate_provider)
        self._dividend_records: Dict[Tuple[str, str, date], Dict] = {}  # (symbol, account_id, date) -> record
        self._current_month_records: Dict[Tuple[str, str, date], Dict] = {}  # 現在月の記録
        self._tax_records: Dict[Tuple[str, str], List[Dict]] = {}  # (symbol, account_id) -> [tax records]

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        return (ActionTypes.is_dividend_action(transaction.action_type) or
                ActionTypes.is_tax_action(transaction.action_type))

    def _create_record_key(self, transaction: Transaction) -> Tuple[str, str, date]:
        """シンボル、アカウント、日付でキーを生成"""
        return (
            transaction.symbol or transaction.description,
            transaction.account_id,
            transaction.transaction_date
        )

    def _process_transaction(self, transaction: Transaction) -> None:
        key = self._create_record_key(transaction)
        tax_key = (key[0], key[1])  # symbol, account_id for tax lookup
        
        if ActionTypes.is_tax_action(transaction.action_type):
            if tax_key not in self._tax_records:
                self._tax_records[tax_key] = []
            self._tax_records[tax_key].append({
                'date': transaction.transaction_date,
                'amount': abs(transaction.amount),
                'description': transaction.description
            })
        else:
            record = {
                'record_date': transaction.transaction_date,
                'account_id': transaction.account_id,
                'symbol': transaction.symbol,
                'description': transaction.description,
                'income_type': self._determine_income_type(transaction),
                'gross_amount': self._create_money(transaction.amount),
                'tax_amount': self._create_money(Decimal('0')),
                'exchange_rate': self._get_exchange_rate(transaction.transaction_date),
                'is_reinvested': 'Reinvest' in transaction.action_type,
                'principal_amount': self._create_money(Decimal('0'))
            }

            # 対応する税金記録を探す
            if tax_key in self._tax_records:
                # 最も日付の近い税金記録を探す
                closest_tax = self._find_closest_tax_record(
                    transaction.transaction_date,
                    self._tax_records[tax_key]
                )
                if closest_tax:
                    record['tax_amount'] = self._create_money(closest_tax['amount'])
                    self._tax_records[tax_key].remove(closest_tax)  # 使用した税金記録を削除

            self._dividend_records[key] = record

    def _find_closest_tax_record(self, target_date: date, tax_records: List[Dict]) -> Optional[Dict]:
        """最も日付の近い税金記録を探す"""
        if not tax_records:
            return None

        # 日付の差が60日以内の税金記録を探す
        valid_records = [
            record for record in tax_records
            if abs((record['date'] - target_date).days) <= 60
        ]

        if not valid_records:
            return None

        # 日付の差が最小のものを返す
        return min(valid_records, key=lambda x: abs((x['date'] - target_date).days))

    def process_all(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """複数トランザクションの一括処理"""
        # 日付でソートしてから処理
        sorted_transactions = sorted(transactions, key=lambda x: x.transaction_date)
        for transaction in sorted_transactions:
            try:
                self.process(transaction)
            except Exception as e:
                self._logger.error(f"Error processing transaction: {e}")
                continue

        # 未処理の税金記録から配当記録を作成
        for tax_key, tax_list in self._tax_records.items():
            for tax in tax_list:
                key = (tax_key[0], tax_key[1], tax['date'])
                if key not in self._dividend_records:
                    self._dividend_records[key] = {
                        'record_date': tax['date'],
                        'account_id': tax_key[1],
                        'symbol': tax_key[0],
                        'description': tax['description'],
                        'income_type': IncomeType.DIVIDEND,
                        'gross_amount': self._create_money(Decimal('0')),
                        'tax_amount': self._create_money(tax['amount']),
                        'exchange_rate': self._get_exchange_rate(tax['date']),
                        'is_reinvested': False,
                        'principal_amount': self._create_money(Decimal('0'))
                    }

        self.records = [
            DividendRecord(**record)
            for record in self._dividend_records.values()
        ]
        return self.get_records()

    def _determine_income_type(self, transaction: Transaction) -> str:
        if ('Interest' in transaction.action_type or 
            'INTEREST' in transaction.action_type):
            return IncomeType.INTEREST
        return IncomeType.DIVIDEND