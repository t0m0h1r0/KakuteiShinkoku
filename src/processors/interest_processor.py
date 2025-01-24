from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date
import logging
from collections import defaultdict

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency, RateProvider
from .base import BaseProcessor
from .interest_records import InterestTradeRecord, InterestSummaryRecord

class InterestTransactionTracker:
    """利子取引の状態を追跡するクラス"""
    def __init__(self):
        self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = defaultdict(lambda: defaultdict(list))
        self._transaction_tracking: Dict[str, Dict] = defaultdict(lambda: {
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0'),
            'matured_dates': set()
        })

    def track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """日次トランザクションを追跡"""
        for transaction in transactions:
            symbol = transaction.symbol or 'GENERAL'
            self._daily_transactions[symbol][transaction.transaction_date].append(transaction)
            if 'MATURED' in transaction.description.upper():
                self._transaction_tracking[symbol]['matured_dates'].add(
                    transaction.transaction_date
                )

    def update_tracking(self, symbol: str, amount: Decimal, tax: Decimal = Decimal('0')) -> None:
        """取引状態を更新"""
        tracking = self._transaction_tracking[symbol]
        tracking['total_amount'] += amount
        tracking['total_tax'] += tax

    def is_matured(self, symbol: str, date: date) -> bool:
        """満期状態のチェック"""
        return date in self._transaction_tracking[symbol]['matured_dates']

    def get_symbol_transactions(self, symbol: str) -> Dict[date, List[Transaction]]:
        """特定のシンボルの全トランザクションを取得"""
        return self._daily_transactions.get(symbol, {})

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(symbol, {
            'total_amount': Decimal('0'),
            'total_tax': Decimal('0'),
            'matured_dates': set()
        })

class InterestProcessor(BaseProcessor):
    """利子処理のメインプロセッサ"""
    def __init__(self):
        super().__init__()
        self._trade_records: List[InterestTradeRecord] = []
        self._summary_records: Dict[str, InterestSummaryRecord] = {}
        self._transaction_tracker = InterestTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def process_all(self, transactions: List[Transaction]) -> List[InterestTradeRecord]:
        """全トランザクションを処理"""
        try:
            # 日次トランザクションの追跡を開始
            self.logger.debug("トランザクションの追跡を開始")
            self._transaction_tracker.track_daily_transactions(transactions)
            
            # シンボルごとに処理
            for symbol, daily_symbol_txs in self._transaction_tracker._daily_transactions.items():
                sorted_dates = sorted(daily_symbol_txs.keys())
                for transaction_date in sorted_dates:
                    transactions_on_date = daily_symbol_txs[transaction_date]
                    self._process_daily_transactions(symbol, transactions_on_date)

            self.logger.info(f"合計 {len(self._trade_records)} の利子レコードを処理")
            return self._trade_records

        except Exception as e:
            self.logger.error(f"利子取引処理中にエラーが発生: {e}")
            return []

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理"""
        try:
            if self._is_tax_transaction(transaction):
                self._process_tax(transaction)
                return

            if not self._is_interest_transaction(transaction):
                return

            self._process_transaction(transaction)

        except Exception as e:
            self.logger.error(f"利子取引の処理中にエラー: {transaction} - {e}")

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        # 税金トランザクションを先に処理
        tax_transactions = [t for t in transactions if self._is_tax_transaction(t)]
        for tax_transaction in tax_transactions:
            self._process_tax(tax_transaction)

        # 利子トランザクションを処理
        interest_transactions = [t for t in transactions if self._is_interest_transaction(t)]
        for transaction in interest_transactions:
            self._process_transaction(transaction)

    def _process_transaction(self, transaction: Transaction) -> None:
        """利子取引の詳細処理"""
        try:
            # 対応する税金を検索
            tax_amount = self._find_matching_tax(transaction)
            
            # 金額の処理
            gross_amount = self._create_money(abs(transaction.amount))
            tax_money = self._create_money(tax_amount)

            # 満期状態の確認
            is_matured = self._transaction_tracker.is_matured(
                transaction.symbol or 'GENERAL',
                transaction.transaction_date
            )

            # 取引レコードの作成
            interest_record = self._create_interest_record(
                transaction, gross_amount, tax_money, is_matured
            )
            
            self._trade_records.append(interest_record)
            self._update_summary_record(interest_record)
            
            # トラッカーの更新
            self._transaction_tracker.update_tracking(
                transaction.symbol or 'GENERAL',
                abs(transaction.amount),
                tax_amount
            )

        except Exception as e:
            self.logger.error(f"利子取引処理中にエラー: {e}")
            raise

    def _is_interest_transaction(self, transaction: Transaction) -> bool:
        """利子トランザクションの判定""" 
        interest_actions = {
            'CREDIT INTEREST',
            'BANK INTEREST',
            'BOND INTEREST',
            'CD INTEREST',
            'PR YR BANK INT',
        }
        return (transaction.action_type.upper() in interest_actions and 
                abs(transaction.amount) > Decimal('0'))

    def _determine_income_type(self, transaction: Transaction) -> str:
        """利子タイプの決定"""
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

    def _create_interest_record(
        self, 
        transaction: Transaction, 
        gross_amount: Money,
        tax_amount: Money,
        is_matured: bool
    ) -> InterestTradeRecord:
        """利子レコードの作成"""
        return InterestTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol or '',
            description=transaction.description,
            income_type=self._determine_income_type(transaction),
            action_type=transaction.action_type,
            is_matured=is_matured,
            gross_amount=gross_amount,
            tax_amount=tax_amount,
            exchange_rate=RateProvider().get_rate(Currency.USD, Currency.JPY, transaction.transaction_date).rate,
        )

    def _update_summary_record(self, interest_record: InterestTradeRecord) -> None:
        """サマリーレコードの更新"""
        symbol = interest_record.symbol or 'GENERAL'
        
        if symbol not in self._summary_records:
            self._summary_records[symbol] = InterestSummaryRecord(
                account_id=interest_record.account_id,
                symbol=symbol,
                description=interest_record.description,
            )
        
        summary = self._summary_records[symbol]
        summary.total_gross_amount += interest_record.gross_amount
        summary.total_tax_amount += interest_record.tax_amount
                              
    def get_records(self) -> List[InterestTradeRecord]:
        """トレードレコードの取得"""
        return sorted(self._trade_records, key=lambda x: x.record_date)

    def get_summary_records(self) -> List[InterestSummaryRecord]:
        """サマリーレコードの取得"""  
        return sorted(self._summary_records.values(), key=lambda x: x.symbol)