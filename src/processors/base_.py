from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Dict, Optional, Any
from datetime import date
from decimal import Decimal
import logging

from ..core.transaction import Transaction
from ..exchange.currency import Currency
from ..exchange.money import Money
from ..exchange.rate_provider import RateProvider
from ..exchange.exchange_rate import ExchangeRate

T = TypeVar('T')

class BaseTransactionTracker:
    """基本トランザクション追跡クラス"""
    def __init__(self):
        self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = {}
        self._transaction_tracking: Dict[str, Dict] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """日次トランザクションを追跡"""
        for transaction in transactions:
            symbol = transaction.symbol or 'GENERAL'
            if symbol not in self._daily_transactions:
                self._daily_transactions[symbol] = {}
            
            date = transaction.transaction_date
            if date not in self._daily_transactions[symbol]:
                self._daily_transactions[symbol][date] = []
            
            self._daily_transactions[symbol][date].append(transaction)

    def get_symbol_transactions(self, symbol: str) -> Dict[date, List[Transaction]]:
        """特定のシンボルの全トランザクションを取得"""
        return self._daily_transactions.get(symbol, {})

    def get_tracking_info(self, symbol: str) -> Dict:
        """特定のシンボルのトラッキング情報を取得"""
        return self._transaction_tracking.get(symbol, {})

class BaseProcessor(ABC, Generic[T]):
    """基本プロセッサクラス"""
    
    def __init__(self):
        self._trade_records: List[T] = []
        self._tax_records: Dict[str, List[Dict]] = {}
        self._matured_symbols: set = set()
        self._rate_provider = RateProvider()
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process(self, transaction: Transaction) -> None:
        """単一トランザクションを処理"""
        pass

    def process_all(self, transactions: List[Transaction]) -> List[T]:
        """全トランザクションを処理"""
        try:
            self.logger.debug("トランザクション一括処理を開始")
            for transaction in transactions:
                try:
                    self.process(transaction)
                except Exception as e:
                    self.logger.error(f"トランザクション処理中にエラー: {transaction} - {e}")
            
            self.logger.info(f"合計 {len(self._trade_records)} レコードを処理")
            return self.get_records()
            
        except Exception as e:
            self.logger.error(f"一括処理中にエラーが発生: {e}")
            return []

    def _get_exchange_rate(self, trade_date: date) -> Decimal:
        """為替レートを取得"""
        rate = self._rate_provider.get_rate(
            base_currency=Currency.USD,
            target_currency=Currency.JPY,
            rate_date=trade_date
        )
        return rate.rate
        
    def _create_money(self, amount: Decimal, reference_date: Optional[date] = None) -> Money:
        """Money オブジェクトを作成"""
        if reference_date is None:
            reference_date = date.today()
        return Money(
            amount=amount,
            currency=Currency.USD,
            reference_date=reference_date
        )

    def _create_money_jpy(self, amount: Decimal) -> Money:
        """JPY Money オブジェクトを作成"""
        return Money(
            amount=amount,
            currency=Currency.JPY,
            reference_date=date.today()
        )

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """税金トランザクションの判定"""
        tax_actions = {
            'NRA TAX ADJ', 'PR YR NRA TAX', 
            'TAX', 'NRA TAX'
        }
        return transaction.action_type.upper() in tax_actions

    def _process_tax(self, transaction: Transaction) -> None:
        """税金トランザクションの処理"""
        try:
            symbol = transaction.symbol or 'GENERAL'
            if symbol not in self._tax_records:
                self._tax_records[symbol] = []
            
            self._tax_records[symbol].append({
                'date': transaction.transaction_date,
                'amount': abs(transaction.amount)
            })
            
            self.logger.debug(f"税金レコードを処理: {symbol} - {abs(transaction.amount)}")
            
        except Exception as e:
            self.logger.error(f"税金処理中にエラー: {transaction} - {e}")
            raise

    def _find_matching_tax(self, transaction: Transaction, max_days: int = 7) -> Decimal:
        """対応する税金を検索"""
        try:
            symbol = transaction.symbol or 'GENERAL'
            if symbol not in self._tax_records:
                return Decimal('0')

            tax_records = self._tax_records[symbol]
            transaction_date = transaction.transaction_date
            
            for tax_record in tax_records:
                if abs((tax_record['date'] - transaction_date).days) <= max_days:
                    return Decimal(tax_record['amount'])

            return Decimal('0')
            
        except Exception as e:
            self.logger.warning(f"税金検索中にエラー: {transaction} - {e}")
            return Decimal('0')

    def _is_matured_transaction(self, transaction: Transaction) -> bool:
        """満期トランザクションの判定"""
        return 'MATURED' in transaction.description.upper()

    def _handle_maturity(self, symbol: str) -> None:
        """満期処理"""
        self._matured_symbols.add(symbol)
        self._trade_records = [r for r in self._trade_records if getattr(r, 'symbol', None) != symbol]

    def get_records(self) -> List[T]:
        """トレードレコードの取得"""
        return sorted(
            self._trade_records,
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )

    @abstractmethod
    def get_summary_records(self) -> List[Any]:
        """サマリーレコードの取得"""
        pass