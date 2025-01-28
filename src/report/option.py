from __future__ import annotations
from typing import Dict, Any, List, Type, TypeVar, Optional
from decimal import Decimal
import logging
from datetime import date

from ..report.interfaces import BaseReportGenerator
from ..processors.option.record import OptionTradeRecord

R = TypeVar('R', bound=OptionTradeRecord)

class OptionTradeReportGenerator(BaseReportGenerator[Dict[str, Any]]):
    """
    オプション取引のレポートを生成するジェネレータ
    
    オプション取引レコードから、レポート出力用の辞書形式データを生成します。
    """
    
    def __init__(self, writer: Any, record_class: Type[R] = OptionTradeRecord):
        """
        OptionTradeReportGeneratorを初期化
        
        Args:
            writer: レポートを書き出すライター
            record_class: 処理するレコードのクラス（デフォルト: OptionTradeRecord）
        """
        super().__init__(writer)
        self.record_class = record_class
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        オプションレコードからレポートデータを生成
        
        Args:
            data: レポート生成に必要なデータを含む辞書
        
        Returns:
            レポート形式の辞書のリスト
        
        Raises:
            ValueError: 必要なデータが見つからない場合
            TypeError: レコードの型が不正な場合
        """
        try:
            # option_recordsが存在しない場合は空リストを使用
            option_records: List[R] = data.get('option_records', [])
            
            # レコードの型チェック
            if option_records and not all(isinstance(r, self.record_class) for r in option_records):
                raise TypeError(f"全てのレコードは {self.record_class.__name__} 型である必要があります")
            
            # レポートデータの生成
            return [self._transform_record(record) for record in option_records]
        
        except KeyError as e:
            self.logger.error(f"必要なデータキーが見つかりません: {e}")
            raise ValueError(f"レポート生成に必要なデータが不足しています: {e}")
        
        except Exception as e:
            self.logger.error(f"オプションレポート生成中にエラー: {e}", exc_info=True)
            raise

    def _transform_record(self, record: R) -> Dict[str, Any]:
        """
        個々のレコードをレポート形式に変換
        
        Args:
            record: 変換元のOptionTradeRecord
        
        Returns:
            レポート形式の辞書
        """
        try:
            return {
                'date': record.record_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'action': record.action,
                'quantity': self._safe_decimal(record.quantity),
                'option_type': record.option_type,
                'strike_price': self._safe_float(record.strike_price),
                'expiry_date': self._format_date(record.expiry_date),
                'underlying': record.underlying,
                'price': self._safe_decimal(record.price.usd),
                'fees': self._safe_decimal(record.fees.usd),
                'trading_pnl': self._safe_decimal(record.trading_pnl.usd),
                'premium_pnl': self._safe_decimal(record.premium_pnl.usd),
                'price_jpy': self._safe_decimal(record.price.jpy),
                'fees_jpy': self._safe_decimal(record.fees.jpy),
                'trading_pnl_jpy': self._safe_decimal(record.trading_pnl.jpy),
                'premium_pnl_jpy': self._safe_decimal(record.premium_pnl.jpy),
                'exchange_rate': self._safe_decimal(record.exchange_rate),
                'position_type': record.position_type,
                'is_closed': record.is_closed,
                'is_expired': record.is_expired,
                'is_assigned': record.is_assigned
            }
        except AttributeError as e:
            self.logger.error(f"レコード変換中に属性エラー: {e}")
            raise TypeError(f"レコードの属性が不正です: {e}")

    @staticmethod
    def _safe_decimal(value: Any) -> Decimal:
        """
        値を安全にDecimalに変換
        
        Args:
            value: 変換する値
        
        Returns:
            Decimal型の値、変換できない場合は0
        """
        try:
            return Decimal(str(value)) if value is not None else Decimal('0')
        except (TypeError, ValueError):
            return Decimal('0')

    @staticmethod
    def _safe_float(value: Any) -> float:
        """
        値を安全にfloatに変換
        
        Args:
            value: 変換する値
        
        Returns:
            float型の値、変換できない場合は0.0
        """
        try:
            return float(value) if value is not None else float(0)
        except (TypeError, ValueError):
            return float(0)

    @staticmethod
    def _format_date(value: Optional[date]) -> str:
        """
        日付を安全に文字列形式に変換
        
        Args:
            value: 変換する日付
        
        Returns:
            'YYYY-MM-DD'形式の日付文字列、Noneの場合は空文字
        """
        try:
            return value.strftime('%Y-%m-%d') if value is not None else ''
        except (AttributeError, TypeError):
            return ''