from __future__ import annotations
from typing import Dict, List, TypeVar, Generic, Union, Optional, Iterator
from decimal import Decimal
import logging

from ..exchange.money import Money
from ..exchange.currency import Currency

R = TypeVar('R')  # レコードの型を表す汎用型

class ReportCalculator(Generic[R]):
    """
    さまざまな金融レポートを計算するためのジェネリックな計算クラス
    
    異なる種類の金融レコードに対して、集計や分析を行うメソッドを提供します。
    """
    
    def __init__(self):
        """
        ReportCalculatorのインスタンスを初期化
        """
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_income_summary(
        self, 
        dividend_records: List[R], 
        interest_records: List[R]
    ) -> Dict[str, Money]:
        """
        収入のサマリーを計算
        
        Args:
            dividend_records: 配当レコードのリスト
            interest_records: 利子レコードのリスト
        
        Returns:
            収入に関する詳細な集計情報
        """
        try:
            # レコードが空の場合のデフォルト値
            if not dividend_records and not interest_records:
                zero_money = Money(Decimal('0'), Currency.USD)
                return {
                    'dividend_total': zero_money,
                    'interest_total': zero_money,
                    'tax_total': zero_money,
                    'net_total': zero_money
                }

            # 配当総額の計算
            dividend_total = self._safe_sum(
                (record.gross_amount for record in dividend_records), 
                Money(Decimal('0'), Currency.USD)
            )

            # 利子総額の計算
            interest_total = self._safe_sum(
                (record.gross_amount for record in interest_records), 
                Money(Decimal('0'), Currency.USD)
            )

            # 税金総額の計算
            tax_total = self._safe_sum(
                (record.tax_amount for record in dividend_records + interest_records), 
                Money(Decimal('0'), Currency.USD)
            )
            
            return {
                'dividend_total': dividend_total,
                'interest_total': interest_total,
                'tax_total': tax_total,
                'net_total': dividend_total + interest_total - tax_total
            }
        except Exception as e:
            self.logger.error(f"収入サマリー計算中にエラー: {e}", exc_info=True)
            raise

    def calculate_stock_summary_details(
        self, 
        records: List[R]
    ) -> Money:
        """
        株式取引のサマリーを計算
        
        Args:
            records: 株式取引レコードのリスト
        
        Returns:
            実現損益の合計
        """
        try:
            return self._safe_sum(
                (record.realized_gain for record in records), 
                Money(Decimal('0'), Currency.USD)
            )
        except Exception as e:
            self.logger.error(f"株式サマリー計算中にエラー: {e}", exc_info=True)
            raise

    def calculate_option_summary_details(
        self, 
        records: List[R]
    ) -> Dict[str, Money]:
        """
        オプション取引のサマリーを計算
        
        Args:
            records: オプション取引レコードのリスト
        
        Returns:
            取引損益、プレミアム収入、手数料の集計
        """
        try:
            return {
                'trading_pnl': self._safe_sum(
                    (record.trading_pnl for record in records), 
                    Money(Decimal('0'), Currency.USD)
                ),
                'premium_pnl': self._safe_sum(
                    (record.premium_pnl for record in records), 
                    Money(Decimal('0'), Currency.USD)
                ),
                'fees': self._safe_sum(
                    (record.fees for record in records), 
                    Money(Decimal('0'), Currency.USD)
                )
            }
        except Exception as e:
            self.logger.error(f"オプションサマリー計算中にエラー: {e}", exc_info=True)
            raise

    def _safe_sum(
        self, 
        iterable: Iterator[Money], 
        initial: Money
    ) -> Money:
        """
        安全に合計を計算するヘルパーメソッド
        
        Args:
            iterable: Moneyオブジェクトの反復可能オブジェクト
            initial: 初期値
        
        Returns:
            合計されたMoney
        """
        try:
            return sum(iterable, initial)
        except TypeError as e:
            self.logger.error(f"合計計算中に型エラー: {e}", exc_info=True)
            raise ValueError("合計計算に失敗しました。要素の型を確認してください。")