from __future__ import annotations
from typing import Dict, Any, List, Type, TypeVar
from decimal import Decimal
import logging

from ..report.interfaces import BaseReportGenerator
from ..processors.stock.record import StockTradeRecord

R = TypeVar("R", bound=StockTradeRecord)


class StockTradeReportGenerator(BaseReportGenerator[Dict[str, Any]]):
    """
    株式取引のレポートを生成するジェネレータ

    株式取引レコードから、レポート出力用の辞書形式データを生成します。
    """

    def __init__(self, writer: Any, record_class: Type[R] = StockTradeRecord):
        """
        StockTradeReportGeneratorを初期化

        Args:
            writer: レポートを書き出すライター
            record_class: 処理するレコードのクラス（デフォルト: StockTradeRecord）
        """
        super().__init__(writer)
        self.record_class = record_class
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        株式取引レコードからレポートデータを生成

        Args:
            data: レポート生成に必要なデータを含む辞書

        Returns:
            レポート形式の辞書のリスト

        Raises:
            ValueError: 必要なデータが見つからない場合
            TypeError: レコードの型が不正な場合
        """
        try:
            # stock_recordsが存在しない場合は空リストを使用
            stock_records: List[R] = data.get("stock_records", [])

            # レコードの型チェック
            if stock_records and not all(
                isinstance(r, self.record_class) for r in stock_records
            ):
                raise TypeError(
                    f"全てのレコードは {self.record_class.__name__} 型である必要があります"
                )

            # レポートデータの生成
            return [self._transform_record(record) for record in stock_records]

        except KeyError as e:
            self.logger.error(f"必要なデータキーが見つかりません: {e}")
            raise ValueError(f"レポート生成に必要なデータが不足しています: {e}")

        except Exception as e:
            self.logger.error(f"株式取引レポート生成中にエラー: {e}", exc_info=True)
            raise

    def _transform_record(self, record: R) -> Dict[str, Any]:
        """
        個々のレコードをレポート形式に変換

        Args:
            record: 変換元のStockTradeRecord

        Returns:
            レポート形式の辞書
        """
        try:
            return {
                "date": record.trade_date,
                "account": record.account_id,
                "symbol": record.symbol,
                "description": record.description,
                "action": record.action,
                "quantity": self._safe_decimal(record.quantity),
                "price": self._safe_decimal(record.price.usd),
                "realized_gain": self._safe_decimal(record.realized_gain.usd),
                "fees": self._safe_decimal(record.fees.usd),
                "price_jpy": self._safe_decimal(record.price.jpy),
                "realized_gain_jpy": self._safe_decimal(record.realized_gain.jpy),
                "fees_jpy": self._safe_decimal(record.fees.jpy),
                "exchange_rate": self._safe_decimal(record.exchange_rate),
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
            return Decimal(str(value)) if value is not None else Decimal("0")
        except (TypeError, ValueError):
            return Decimal("0")
