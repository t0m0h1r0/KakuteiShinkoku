from decimal import Decimal
from typing import Dict, Tuple, List
from datetime import date, timedelta

from .base import BaseProcessor
from src.core.types.transaction import Transaction
from src.core.types.money import Money
from src.core.interfaces import IExchangeRateProvider

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
                 is_reinvested: bool,
                 principal_amount: Money = Money(Decimal('0'))):
        self.record_date = record_date
        self.account_id = account_id
        self.symbol = symbol
        self.description = description
        self.income_type = income_type
        self.gross_amount = gross_amount
        self.tax_amount = tax_amount
        self.exchange_rate = exchange_rate
        self.is_reinvested = is_reinvested
        self.principal_amount = principal_amount

class DividendProcessor(BaseProcessor[DividendRecord]):
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._dividend_records: Dict[Tuple[str, str, date], Dict] = {}
        self._tax_records: Dict[str, Dict[date, Decimal]] = {}

    def process(self, transaction: Transaction) -> None:
        """トランザクションを処理"""
        if self._is_dividend_transaction(transaction):
            self._process_dividend(transaction)
        elif self._is_tax_transaction(transaction):
            self._process_tax(transaction)

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当トランザクションかどうかを判定"""
        dividend_keywords = ['DIVIDEND', 'INTEREST', 'CD INTEREST']
        return any(keyword in transaction.action_type.upper() for keyword in dividend_keywords)

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """税金トランザクションかどうかを判定"""
        return 'TAX' in transaction.action_type.upper()

    def _process_tax(self, transaction: Transaction) -> None:
        """税金トランザクションを処理"""
        if transaction.symbol not in self._tax_records:
            self._tax_records[transaction.symbol] = {}
        
        self._tax_records[transaction.symbol][transaction.transaction_date] = abs(transaction.amount)

    def _process_dividend(self, transaction: Transaction) -> None:
        """配当トランザクションを処理"""
        tax_amount = self._find_matching_tax(transaction)
        
        dividend_record = DividendRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            income_type=self._determine_income_type(transaction),
            gross_amount=Money(transaction.amount),
            tax_amount=Money(tax_amount),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            is_reinvested='REINVEST' in transaction.action_type.upper()
        )
        
        self.records.append(dividend_record)

    def _find_matching_tax(self, transaction: Transaction) -> Decimal:
        """対応する税金を検索"""
        if transaction.symbol not in self._tax_records:
            return Decimal('0')

        tax_records = self._tax_records[transaction.symbol]
        for tax_date, tax_amount in tax_records.items():
            # 同日または前後3日以内の税金を探す
            if abs((tax_date - transaction.transaction_date).days) <= 3:
                return tax_amount

        return Decimal('0')

    def _determine_income_type(self, transaction: Transaction) -> str:
        """収入の種類を判定"""
        if 'INTEREST' in transaction.action_type.upper():
            return 'Interest'
        elif 'CD INTEREST' in transaction.action_type.upper():
            return 'CD Interest'
        return 'Dividend'

    def process_all(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """複数トランザクションの処理"""
        # 日付でソート
        sorted_transactions = sorted(transactions, key=lambda x: x.transaction_date)
        
        # まず税金記録を処理
        tax_transactions = [t for t in sorted_transactions if self._is_tax_transaction(t)]
        for transaction in tax_transactions:
            self._process_tax(transaction)
        
        # 配当記録を処理
        dividend_transactions = [t for t in sorted_transactions if self._is_dividend_transaction(t)]
        for transaction in dividend_transactions:
            self._process_dividend(transaction)
        
        return self.get_records()
