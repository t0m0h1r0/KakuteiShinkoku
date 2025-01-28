from __future__ import annotations
from typing import Dict, Any, List, Type, TypeVar
from decimal import Decimal
import logging

from ..report.interfaces import BaseReportGenerator
from ..processors.dividend.record import DividendTradeRecord

R = TypeVar("R", bound=DividendTradeRecord)


class DividendReportGenerator(BaseReportGenerator[Dict[str, Any]]):
    """
    配当取引のレポートを生成するジェネレータ

    配当取引レコードから、レポート出力用の辞書形式データを生成します。
    """

    def __init__(self, writer: Any, record_class: Type[R] = DividendTradeRecord):
        """
        DividendReportGeneratorを初期化

        Args:
            writer: レポートを書き出すライター
            record_class: 処理するレコードのクラス（デフォルト: DividendTradeRecord）
        """
        super().__init__(writer)
        self.record_class = record_class
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        配当レコードからレポートデータを生成

        Args:
            data: レポート生成に必要なデータを含む辞書

        Returns:
            レポート形式の辞書のリスト

        Raises:
            ValueError: 必要なデータが見つからない場合
            TypeError: レコードの型が不正な場合
        """
        try:
            # dividend_recordsが存在しない場合は空リストを使用
            dividend_records: List[R] = data.get("dividend_records", [])

            # レコードの型チェック
            if dividend_records and not all(
                isinstance(r, self.record_class) for r in dividend_records
            ):
                raise TypeError(
                    f"全てのレコードは {self.record_class.__name__} 型である必要があります"
                )

            # レポートデータの生成
            return [self._transform_record(record) for record in dividend_records]

        except KeyError as e:
            self.logger.error(f"必要なデータキーが見つかりません: {e}")
            raise ValueError(f"レポート生成に必要なデータが不足しています: {e}")

        except Exception as e:
            self.logger.error(f"配当レポート生成中にエラー: {e}", exc_info=True)
            raise

    def _transform_record(self, record: R) -> Dict[str, Any]:
        """
        個々のレコードをレポート形式に変換

        Args:
            record: 変換元のDividendTradeRecord

        Returns:
            レポート形式の辞書
        """
        try:
            return {
                "date": record.record_date,
                "account": record.account_id,
                "symbol": record.symbol,
                "description": record.description,
                "action_type": record.action_type,
                "income_type": record.income_type,
                "gross_amount": self._safe_decimal(record.gross_amount.usd),
                "tax_amount": self._safe_decimal(record.tax_amount.usd),
                "net_amount": self._safe_decimal(record.net_amount.usd),
                "gross_amount_jpy": self._safe_decimal(record.gross_amount.jpy),
                "tax_amount_jpy": self._safe_decimal(record.tax_amount.jpy),
                "net_amount_jpy": self._safe_decimal(record.net_amount.jpy),
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
