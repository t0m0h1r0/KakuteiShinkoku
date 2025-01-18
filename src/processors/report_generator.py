from typing import Dict, List, Any
import logging
from abc import ABC, abstractmethod

from ..core.interfaces import IWriter
from ..app.context import ApplicationContext

class ReportGenerator(ABC):
    """レポート生成の基本クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def generate_report(self, data: Dict[str, Any]) -> None:
        """レポート生成の抽象メソッド"""
        pass

class InvestmentReportGenerator(ReportGenerator):
    """投資レポート生成クラス"""
    
    def generate_report(self, data: Dict[str, Any]) -> None:
        """投資レポートの生成"""
        try:
            dividend_records = data.get('dividend_records', [])
            trade_records = data.get('trade_records', [])

            # 株式取引とオプション取引の分離
            stock_trades = [r for r in trade_records if r.trade_type != 'Option']
            option_trades = [r for r in trade_records if r.trade_type == 'Option']

            # 各種レポートの生成
            self._write_dividend_report(dividend_records)
            self._write_trade_reports(stock_trades, option_trades)
            self._write_summary_report(dividend_records, trade_records)

        except Exception as e:
            self.logger.error(f"Report generation error: {e}", exc_info=True)
            raise

    def _write_dividend_report(self, dividend_records: List) -> None:
        """配当レポートの生成"""
        formatted_records = [self._format_dividend_record(r) for r in dividend_records]
        self.context.writers['dividend_csv'].output(formatted_records)
        self.context.writers['console'].output(dividend_records)

    def _write_trade_reports(self, stock_trades: List, option_trades: List) -> None:
        """取引レポートの生成"""
        # 株式取引レポート
        stock_records = [self._format_trade_record(r, 'stock') for r in stock_trades]
        self.context.writers['stock_trade_csv'].output(stock_records)

        # オプション取引レポート
        option_records = [self._format_trade_record(r, 'option') for r in option_trades]
        self.context.writers['option_trade_csv'].output(option_records)

    def _write_summary_report(self, dividend_records: List, trade_records: List) -> None:
        """サマリーレポートの生成"""
        summary = self._calculate_summary(dividend_records, trade_records)
        self.context.writers['profit_loss_csv'].output([summary])

    def _format_dividend_record(self, record):
        """配当記録のフォーマット"""
        return {
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.income_type,
            'gross_amount': record.gross_amount.amount,
            'tax_amount': record.tax_amount.amount,
            'net_amount': record.gross_amount.amount - record.tax_amount.amount
        }

    def _format_trade_record(self, record, trade_type='stock'):
        """取引記録のフォーマット"""
        if trade_type == 'stock':
            return {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'type': record.trade_type,
                'action': record.action,
                'quantity': record.quantity,
                'price': record.price.amount
            }
        else:
            return {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'expiry_date': record.expiry_date,
                'strike_price': record.strike_price,
                'option_type': record.option_type,
                'position_type': record.position_type,
                'description': record.description,
                'action': record.action,
                'quantity': record.quantity,
                'premium_or_gain': record.premium_or_gain.amount if record.premium_or_gain else record.price.amount,
                'is_expired': record.is_expired
            }

    def _calculate_summary(self, dividend_records: List, trade_records: List) -> Dict:
        """サマリー情報の計算"""
        # 実装は省略 - 必要に応じて追加
        return {}