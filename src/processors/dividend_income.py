from decimal import Decimal
from typing import Optional, List, Dict
from datetime import date, timedelta

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor

class DividendRecord:
    def __init__(self, 
                 record_date: date, 
                 account_id: str, 
                 symbol: str, 
                 description: str, 
                 income_type: str, 
                 gross_amount: Money, 
                 tax_amount: Money,
                 exchange_rate: Decimal,
                 is_reinvested: bool):
        self.record_date = record_date
        self.account_id = account_id
        self.symbol = symbol
        self.description = description
        self.income_type = income_type
        self.gross_amount = gross_amount
        self.tax_amount = tax_amount
        self.exchange_rate = exchange_rate
        self.is_reinvested = is_reinvested

class DividendProcessor(BaseProcessor[DividendRecord]):
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._tax_records: Dict[str, List[dict]] = {}
    
    def process(self, transaction: Transaction) -> None:
        """トランザクションを処理"""
        if self._is_dividend_transaction(transaction):
            self._process_dividend(transaction)
        elif self._is_tax_transaction(transaction):
            self._process_tax(transaction)

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当トランザクションかどうかを判定"""
        dividend_keywords = ['DIVIDEND', 'REINVEST DIVIDEND']
        return any(keyword in transaction.action_type.upper() for keyword in dividend_keywords)

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """税金トランザクションかどうかを判定"""
        return 'TAX' in transaction.action_type.upper()

    def _process_tax(self, transaction: Transaction) -> None:
        """税金トランザクションを処理"""
        symbol = transaction.symbol or 'GENERAL'
        if symbol not in self._tax_records:
            self._tax_records[symbol] = []
        
        self._tax_records[symbol].append({
            'date': transaction.transaction_date,
            'amount': abs(transaction.amount)
        })

    def _process_dividend(self, transaction: Transaction) -> None:
        """配当トランザクションを処理"""
        tax_amount = self._find_matching_tax(transaction)
        
        dividend_record = DividendRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            income_type='Dividend',  # 固定値
            gross_amount=Money(transaction.amount),
            tax_amount=Money(tax_amount),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            is_reinvested='REINVEST' in transaction.action_type.upper()
        )
        
        self.records.append(dividend_record)

    def _find_matching_tax(self, transaction: Transaction) -> Decimal:
        """対応する税金を検索"""
        symbol = transaction.symbol or 'GENERAL'
        if symbol not in self._tax_records:
            return Decimal('0')

        tax_records = self._tax_records[symbol]
        transaction_date = transaction.transaction_date
        
        # 1週間前から1週間後までの税金レコードを検索
        for tax_record in tax_records:
            # 税金記録の日付が配当の前後1週間以内
            if abs((tax_record['date'] - transaction_date).days) <= 7:
                return Decimal(tax_record['amount'])

        return Decimal('0')
