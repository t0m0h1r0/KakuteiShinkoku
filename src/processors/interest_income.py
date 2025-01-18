from decimal import Decimal
from typing import Optional, List, Dict
from datetime import date, timedelta

from ..core.types.transaction import Transaction
from ..core.types.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor

class InterestRecord:
    def __init__(self, 
                 record_date: date, 
                 account_id: str, 
                 symbol: str,
                 description: str, 
                 income_type: str,
                 gross_amount: Money, 
                 tax_amount: Money,
                 exchange_rate: Decimal,
                 is_matured: bool = False):
        self.record_date = record_date
        self.account_id = account_id
        self.symbol = symbol
        self.description = description
        self.income_type = income_type
        self.gross_amount = gross_amount
        self.tax_amount = tax_amount
        self.exchange_rate = exchange_rate
        self.is_matured = is_matured

class InterestProcessor(BaseProcessor[InterestRecord]):
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._tax_records: Dict[str, List[dict]] = {}
    
    def process(self, transaction: Transaction) -> None:
        """トランザクションを処理"""
        # デバッグ用のログ出力
        print(f"処理中のトランザクション: Date: {transaction.transaction_date}, Action: {transaction.action_type}, Amount: {transaction.amount}")
        
        if self._is_interest_transaction(transaction):
            self._process_interest(transaction)
        elif self._is_tax_transaction(transaction):
            self._process_tax(transaction)

    def _is_interest_transaction(self, transaction: Transaction) -> bool:
        """利子トランザクションかどうかを判定"""
        interest_keywords = [
            'INTEREST', 'BANK INTEREST', 'CREDIT INTEREST', 
            'CD INTEREST', 'CD MATURITY', 
            'BANK INT', 
            'CREDIT INT',
            'SCHWAB1 INT',
            'CREDIT INTEREST'  # 新たに追加
        ]
        
        # キーワードのチェック（大文字・小文字を区別しない）
        is_interest = any(
            keyword.upper() in transaction.action_type.upper() or 
            keyword.upper() in transaction.description.upper() 
            for keyword in interest_keywords
        )
        
        # 金額が0でない場合のみ利子として扱う
        is_interest = is_interest and abs(transaction.amount) > Decimal('0')
        
        # デバッグ出力
        if is_interest:
            print(f"利子トランザクション検出: "
                f"Date: {transaction.transaction_date}, "
                f"Action: {transaction.action_type}, "
                f"Description: {transaction.description}, "
                f"Amount: {transaction.amount}")
        
        return is_interest

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

    def _process_interest(self, transaction: Transaction) -> None:
        """利子トランザクションを処理"""
        tax_amount = self._find_matching_tax(transaction)
        
        # income_typeの判定を修正
        if 'CD INTEREST' in transaction.action_type.upper() or \
        'CD MATURITY' in transaction.action_type.upper():
            income_type = 'CD Interest'
        elif 'BOND INTEREST' in transaction.action_type.upper():
            income_type = 'Bond Interest'
        else:
            income_type = 'Interest'
        
        interest_record = InterestRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type=income_type,
            gross_amount=Money(abs(transaction.amount)),
            tax_amount=Money(tax_amount),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            is_matured='MATURITY' in transaction.action_type.upper()
        )
        
        self.records.append(interest_record)

    def _find_matching_tax(self, transaction: Transaction) -> Decimal:
        """対応する税金を検索"""
        symbol = transaction.symbol or 'GENERAL'
        if symbol not in self._tax_records:
            return Decimal('0')

        tax_records = self._tax_records[symbol]
        transaction_date = transaction.transaction_date
        
        # 1週間前から1週間後までの税金レコードを検索
        for tax_record in tax_records:
            # 税金記録の日付が利子の前後1週間以内
            if abs((tax_record['date'] - transaction_date).days) <= 7:
                return Decimal(tax_record['amount'])

        return Decimal('0')