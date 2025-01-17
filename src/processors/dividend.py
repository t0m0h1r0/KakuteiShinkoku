from decimal import Decimal
from typing import Dict, Tuple, List, Optional
from datetime import datetime, date, timedelta

from .base import BaseProcessor
from src.core.models import Transaction, DividendRecord, Money
from src.config.action_types import ActionTypes
from src.config.constants import Currency, IncomeType

class DividendProcessor(BaseProcessor[DividendRecord]):
    def __init__(self, exchange_rate_provider):
        super().__init__(exchange_rate_provider)
        self._dividend_records: Dict[Tuple[str, str, date], Dict] = {}  # (symbol, account_id, date) -> record
        self._tax_records: Dict[str, Dict[date, Decimal]] = {}  # symbol -> {date: tax_amount}

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        return (ActionTypes.is_dividend_action(transaction.action_type) or
                ActionTypes.is_tax_action(transaction.action_type))

    def _process_transaction(self, transaction: Transaction) -> None:
        """トランザクションを処理"""
        if ActionTypes.is_tax_action(transaction.action_type):
            self._process_tax(transaction)
        else:
            self._process_dividend(transaction)

    def _process_tax(self, transaction: Transaction) -> None:
        """税金トランザクションを処理"""
        symbol = transaction.symbol
        if symbol not in self._tax_records:
            self._tax_records[symbol] = {}
        self._tax_records[symbol][transaction.transaction_date] = abs(transaction.amount)

    def _process_dividend(self, transaction: Transaction) -> None:
        """配当トランザクションを処理"""
        key = (
            transaction.symbol,
            transaction.account_id,
            transaction.transaction_date
        )

        # 対応する税金を検索
        tax_amount = self._find_matching_tax(
            transaction.symbol,
            transaction.transaction_date
        )

        record = {
            'record_date': transaction.transaction_date,
            'account_id': transaction.account_id,
            'symbol': transaction.symbol,
            'description': transaction.description,
            'income_type': self._determine_income_type(transaction),
            'gross_amount': self._create_money(transaction.amount),
            'tax_amount': self._create_money(tax_amount),
            'exchange_rate': self._get_exchange_rate(transaction.transaction_date),
            'is_reinvested': 'Reinvest' in transaction.action_type,
            'principal_amount': self._create_money(Decimal('0'))
        }

        self._dividend_records[key] = record

    def _find_matching_tax(self, symbol: str, dividend_date: date) -> Decimal:
        """配当に対応する税金を検索"""
        if symbol not in self._tax_records:
            return Decimal('0')

        # 同じ日付の税金を探す
        if dividend_date in self._tax_records[symbol]:
            return self._tax_records[symbol][dividend_date]

        # 前後3日以内の税金を探す
        for i in range(1, 4):
            # 後の日付を確認
            future_date = dividend_date + timedelta(days=i)
            if future_date in self._tax_records[symbol]:
                return self._tax_records[symbol][future_date]

            # 前の日付を確認
            past_date = dividend_date - timedelta(days=i)
            if past_date in self._tax_records[symbol]:
                return self._tax_records[symbol][past_date]

        return Decimal('0')

    def _determine_income_type(self, transaction: Transaction) -> str:
        if ('Interest' in transaction.action_type or 
            'INTEREST' in transaction.action_type):
            return IncomeType.INTEREST
        return IncomeType.DIVIDEND

    def process_all(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """複数のトランザクションを処理"""
        # 日付でソートしてから処理
        sorted_transactions = sorted(transactions, key=lambda x: x.transaction_date)
        
        # まず税金記録を処理
        tax_transactions = [t for t in sorted_transactions if ActionTypes.is_tax_action(t.action_type)]
        for transaction in tax_transactions:
            self._process_tax(transaction)
        
        # 次に配当記録を処理
        dividend_transactions = [t for t in sorted_transactions if ActionTypes.is_dividend_action(t.action_type)]
        for transaction in dividend_transactions:
            self._process_dividend(transaction)
        
        self.records = [
            DividendRecord(**record)
            for record in self._dividend_records.values()
        ]

        return self.get_records()