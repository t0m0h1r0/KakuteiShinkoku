from decimal import Decimal
from typing import Dict, List
from datetime import date

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .interest_records import InterestTradeRecord, InterestSummaryRecord

class InterestProcessor(BaseProcessor):
    """利子取引処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        # 税金記録の管理
        self._tax_records: Dict[str, List[dict]] = {}
        # 取引記録の管理
        self._trade_records: List[InterestTradeRecord] = []
        # サマリー記録の管理
        self._summary_records: Dict[str, InterestSummaryRecord] = {}

    def process(self, transaction: Transaction) -> None:
        """トランザクションの処理"""
        # 利子トランザクションかどうかを判定
        if not self._is_interest_transaction(transaction):
            return

        # 税金トランザクションの処理
        if self._is_tax_transaction(transaction):
            self._process_tax(transaction)
            return

        # 利子トランザクションの処理
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)
        
        # 税金の検索
        tax_amount = self._find_matching_tax(transaction)
        
        # 金額オブジェクトの作成
        gross_amount = Money(abs(transaction.amount), Currency.USD)
        tax_money = Money(tax_amount, Currency.USD)

        # 取引記録の作成
        interest_record = InterestTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type=self._determine_income_type(transaction),
            action_type=transaction.action_type,
            is_matured='MATURED' in transaction.description.upper(),
            gross_amount=gross_amount,
            tax_amount=tax_money,
            exchange_rate=exchange_rate
        )
        
        # 取引記録の追加
        self._trade_records.append(interest_record)
        
        # サマリーレコードの更新
        self._update_summary_record(interest_record)

    def _is_interest_transaction(self, transaction: Transaction) -> bool:
        """利子トランザクションかどうかを判定"""
        interest_actions = {
            'CREDIT INTEREST',
            'BANK INTEREST',
            'BOND INTEREST',
            'CD INTEREST',
            'PR YR BANK INT',
        }
        
        # アクションタイプをチェック
        is_interest = transaction.action_type.upper() in interest_actions
        
        # 金額が0でない場合のみ利子として扱う
        return is_interest and abs(transaction.amount) > Decimal('0')

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

    def _find_matching_tax(self, transaction: Transaction) -> Decimal:
        """対応する税金を検索"""
        symbol = transaction.symbol or 'GENERAL'
        if symbol not in self._tax_records:
            return Decimal('0')

        tax_records = self._tax_records[symbol]
        transaction_date = transaction.transaction_date
        
        # 1週間前から1週間後までの税金レコードを検索
        for tax_record in tax_records:
            if abs((tax_record['date'] - transaction_date).days) <= 7:
                return Decimal(tax_record['amount'])

        return Decimal('0')

    def _determine_income_type(self, transaction: Transaction) -> str:
        """収入タイプを判定"""
        action = transaction.action_type.upper()
        
        if action == 'CD INTEREST':
            return 'CD Interest'
        elif action == 'BOND INTEREST':
            return 'Bond Interest'
        elif action == 'BANK INTEREST':
            return 'Bank Interest'
        elif action == 'CREDIT INTEREST':
            return 'Credit Interest'
        return 'Other Interest'

    def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
        """サマリーレコードを更新"""
        symbol = interest_record.symbol or 'GENERAL'
        
        # サマリーレコードが存在しない場合は作成
        if symbol not in self._summary_records:
            self._summary_records[symbol] = InterestSummaryRecord(
                account_id=interest_record.account_id,
                symbol=symbol,
                description=interest_record.description,
                exchange_rate=interest_record.exchange_rate
            )
        
        summary = self._summary_records[symbol]
        
        # 金額の累積
        summary.total_gross_amount += interest_record.gross_amount
        summary.total_tax_amount += interest_record.tax_amount

    def get_records(self) -> List[InterestTradeRecord]:
        """取引記録を取得"""
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリー記録を取得"""
        return sorted(
            self._summary_records.values(), 
            key=lambda x: x.symbol
        )