import re
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .dividend_records import DividendTradeRecord, DividendSummaryRecord

class DividendProcessor(BaseProcessor):
    """配当処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        # 税金記録の管理
        self._tax_records: Dict[str, List[dict]] = {}
        # 取引記録の管理
        self._trade_records: List[DividendTradeRecord] = []
        # サマリー記録の管理
        self._summary_records: Dict[str, DividendSummaryRecord] = {}

    def process(self, transaction: Transaction) -> None:
        """トランザクションの処理"""
        # 税金トランザクションの処理（先に判定）
        if self._is_tax_transaction(transaction):
            self._process_tax(transaction)
            return

        # 配当トランザクションかどうかを判定
        if not self._is_dividend_transaction(transaction):
            return

        # 配当トランザクションの処理
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)
        
        # 税金の検索
        tax_amount = self._find_matching_tax(transaction)
        
        # 金額オブジェクトの作成
        gross_amount = Money(abs(transaction.amount), Currency.USD)
        tax_money = Money(tax_amount, Currency.USD)

        # 取引記録の作成
        dividend_record = DividendTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type='Dividend',
            action_type=transaction.action_type,
            gross_amount=gross_amount,
            tax_amount=tax_money,
            exchange_rate=exchange_rate
        )
        
        # 取引記録の追加
        self._trade_records.append(dividend_record)
        
        # サマリーレコードの更新
        self._update_summary_record(dividend_record)

    def _is_dividend_transaction(self, transaction: Transaction) -> bool:
        """配当トランザクションかどうかを判定"""
        dividend_actions = {
            'DIVIDEND', 
            'CASH DIVIDEND',
            'REINVEST DIVIDEND',
            'PR YR CASH DIV'
        }
        
        # アクションタイプをチェック
        return (transaction.action_type.upper() in dividend_actions and 
                abs(transaction.amount) > Decimal('0'))

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """税金トランザクションかどうかを判定"""
        tax_actions = {
            'NRA TAX ADJ',
            'PR YR NRA TAX'
        }
        return transaction.action_type.upper() in tax_actions

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

    def _update_summary_record(self, dividend_record: DividendTradeRecord) -> None:
        """サマリーレコードを更新"""
        symbol = dividend_record.symbol or 'GENERAL'
        
        # サマリーレコードが存在しない場合は作成
        if symbol not in self._summary_records:
            self._summary_records[symbol] = DividendSummaryRecord(
                account_id=dividend_record.account_id,
                symbol=symbol,
                description=dividend_record.description,
                exchange_rate=dividend_record.exchange_rate
            )
        
        summary = self._summary_records[symbol]
        
        # 金額の累積
        summary.total_gross_amount += dividend_record.gross_amount
        summary.total_tax_amount += dividend_record.tax_amount

    def get_records(self) -> List[DividendTradeRecord]:
        """取引記録を取得"""
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[DividendSummaryRecord]:
        """サマリー記録を取得"""
        return sorted(
            self._summary_records.values(), 
            key=lambda x: x.symbol
        )