from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Any, Dict
from datetime import date
from decimal import Decimal
import logging

from ...core.tx import Transaction
from ...exchange.currency import Currency
from ...exchange.money import Money
from ...exchange.exchange import exchange

T = TypeVar('T')

class BaseProcessor(ABC, Generic[T]):
    """基本処理クラス"""
    
    def __init__(self):
        self._trade_records: List[T] = []
        self._tax_records: Dict[str, List[Dict]] = {}
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

    def _create_money(self, amount: Decimal, reference_date: Optional[date] = None) -> Money:
        """Money オブジェクトを作成"""
        if reference_date is None:
            reference_date = date.today()
        return Money(
            amount=amount,
            currency=Currency.USD,
            rate_date=reference_date
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