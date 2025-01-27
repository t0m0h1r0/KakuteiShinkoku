"""
取引処理の基底クラスモジュール

このモジュールは、各種取引処理クラスの基底となる抽象クラスを提供します。
全ての具象プロセッサクラスはこのクラスを継承して実装します。
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Dict, Any
from decimal import Decimal
import logging
from datetime import date
from collections.abc import Iterable

from ...core.tx import Transaction
from ...exchange.money import Money
from ...exchange.currency import Currency
from ...exchange.exchange import exchange
from .record import BaseTradeRecord, BaseSummaryRecord
from ...core.error import ProcessingError

T = TypeVar('T', bound=BaseTradeRecord)
R = TypeVar('R', bound=BaseSummaryRecord)

class BaseProcessor(ABC, Generic[T, R]):
    """取引処理の基底クラス
    
    全ての具象プロセッサクラスはこのクラスを継承します。
    取引データの処理と集計を行うための共通機能を提供します。
    
    Attributes:
        _trade_records (List[T]): 取引記録のリスト
        _tax_records (Dict[str, List[Dict[str, Any]]]): 税金記録の辞書
        _summary_records (Dict[str, R]): サマリー記録の辞書
        _rate_provider: 為替レートプロバイダ
        logger: ロガーインスタンス
    """
    
    def __init__(self) -> None:
        """初期化処理"""
        self._trade_records: List[T] = []
        self._tax_records: Dict[str, List[Dict[str, Any]]] = {}
        self._summary_records: Dict[str, R] = {}
        self._rate_provider = exchange
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_tracker()

    def _initialize_tracker(self) -> None:
        """トランザクショントラッカーの初期化"""
        self._transaction_tracker = None

    def process_all(self, transactions: List[Transaction]) -> List[T]:
        """複数のトランザクションを一括処理
        
        Args:
            transactions: 処理対象のトランザクションリスト
            
        Returns:
            処理済みの取引記録リスト
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            if not isinstance(transactions, Iterable):
                raise ValueError("transactions must be iterable")

            self.logger.debug(f"一括処理開始: 合計{len(transactions)}件")
            
            self._initialize_batch_processing(transactions)
            self._execute_daily_processing()
            
            self.logger.info(f"処理完了: {len(self._trade_records)}件の記録を生成")
            return self.get_records()
            
        except Exception as e:
            self.logger.error(f"一括処理中にエラー発生: {e}")
            raise ProcessingError(f"一括処理に失敗: {e}")

    def _initialize_batch_processing(self, transactions: List[Transaction]) -> None:
        """一括処理の初期化
        
        Args:
            transactions: 処理対象のトランザクションリスト
        """
        if hasattr(self, '_transaction_tracker') and self._transaction_tracker:
            self._transaction_tracker.track_daily_transactions(transactions)

    def _execute_daily_processing(self) -> None:
        """日次処理の実行"""
        if hasattr(self, '_transaction_tracker'):
            for symbol, daily_txs in self._transaction_tracker._daily_transactions.items():
                for transaction_date in sorted(daily_txs.keys()):
                    self._process_daily_transactions(
                        symbol, 
                        daily_txs[transaction_date]
                    )

    @abstractmethod
    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理
        
        Args:
            transaction: 処理対象のトランザクション
            
        Raises:
            NotImplementedError: 具象クラスで実装されていない場合
        """
        pass

    @abstractmethod
    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理
        
        Args:
            symbol: 取引銘柄
            transactions: 処理対象のトランザクションリスト
            
        Raises:
            NotImplementedError: 具象クラスで実装されていない場合
        """
        pass

    def _create_money(
        self, 
        amount: Decimal, 
        reference_date: Optional[date] = None
    ) -> Money:
        """Money オブジェクトの生成
        
        Args:
            amount: 金額
            reference_date: 為替レート参照日
            
        Returns:
            生成されたMoneyオブジェクト
            
        Raises:
            ValueError: 金額が不正な場合
        """
        if not isinstance(amount, (Decimal, int, float)):
            raise ValueError("amount must be a numeric value")

        reference_date = reference_date or date.today()
        
        try:
            self.logger.debug(f"Money作成: {amount} USD @ {reference_date}")
            return Money(
                amount=Decimal(str(amount)),
                currency=Currency.USD,
                rate_date=reference_date
            )
        except Exception as e:
            self.logger.error(f"Money作成エラー: {e}")
            raise ValueError(f"Money作成に失敗: {e}")

    def _is_tax_transaction(self, transaction: Transaction) -> bool:
        """税金取引の判定
        
        Args:
            transaction: 判定対象のトランザクション
            
        Returns:
            税金取引の場合True
        """
        tax_actions = {
            'NRA TAX ADJ', 'PR YR NRA TAX', 
            'TAX', 'NRA TAX'
        }
        is_tax = transaction.action_type.upper() in tax_actions
        self.logger.debug(f"税金取引判定: {transaction.action_type} -> {is_tax}")
        return is_tax

    def _process_tax(self, transaction: Transaction) -> None:
        """税金トランザクションの処理
        
        Args:
            transaction: 処理対象の税金トランザクション
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
        """
        try:
            symbol = transaction.symbol or 'GENERAL'
            if symbol not in self._tax_records:
                self._tax_records[symbol] = []
            
            self._tax_records[symbol].append({
                'date': transaction.transaction_date,
                'amount': abs(transaction.amount)
            })
            
            self.logger.debug(f"税金記録: {symbol} - {abs(transaction.amount)}")
            
        except Exception as e:
            self.logger.error(f"税金処理エラー: {e}")
            raise ProcessingError(f"税金処理に失敗: {e}")

    def _find_matching_tax(
        self, 
        transaction: Transaction, 
        max_days: int = 7
    ) -> Decimal:
        """対応する税金の検索
        
        Args:
            transaction: 対象トランザクション
            max_days: 検索対象期間（日数）
            
        Returns:
            見つかった税金額（見つからない場合は0）
        """
        try:
            symbol = transaction.symbol or 'GENERAL'
            self.logger.debug(f"税金検索: {symbol} @ {transaction.transaction_date}")
            
            if symbol not in self._tax_records:
                return Decimal('0')

            tax_records = self._tax_records[symbol]
            transaction_date = transaction.transaction_date
            
            for tax_record in tax_records:
                if abs((tax_record['date'] - transaction_date).days) <= max_days:
                    return Decimal(str(tax_record['amount']))

            return Decimal('0')
            
        except Exception as e:
            self.logger.warning(f"税金検索エラー: {e}")
            return Decimal('0')

    def get_records(self) -> List[T]:
        """取引記録の取得
        
        Returns:
            ソート済みの取引記録リスト
        """
        return sorted(
            self._trade_records,
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )

    @abstractmethod
    def get_summary_records(self) -> List[R]:
        """サマリー記録の取得
        
        Returns:
            サマリー記録のリスト
            
        Raises:
            NotImplementedError: 具象クラスで実装されていない場合
        """
        pass

    def _create_trade_record(self, **kwargs) -> T:
        """取引記録の作成
        
        Args:
            **kwargs: 取引記録の属性
            
        Returns:
            生成された取引記録
        """
        return self._record_class(**kwargs)

    def _create_summary_record(self, **kwargs) -> R:
        """サマリー記録の作成
        
        Args:
            **kwargs: サマリー記録の属性
            
        Returns:
            生成されたサマリー記録
        """
        return self._summary_class(**kwargs)