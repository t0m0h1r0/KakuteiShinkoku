from typing import Dict, List, Any
from decimal import Decimal
import logging
from abc import ABC, abstractmethod

from ..core.interfaces import IWriter
from ..app.application_context import ApplicationContext
from ..processors.trade_records import StockTradeRecord, OptionTradeRecord, PremiumRecord
from ..processors.interest_income import InterestRecord
from ..processors.dividend_income import DividendRecord

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
            # 各種レコードの取得
            dividend_records = data.get('dividend_records', [])
            interest_records = data.get('interest_records', [])
            stock_records = data.get('stock_records', [])
            option_records = data.get('option_records', [])
            premium_records = data.get('premium_records', [])

            # 各種レポートの生成
            self._write_dividend_report(dividend_records)
            self._write_interest_report(interest_records)
            self._write_stock_report(stock_records)
            self._write_option_report(option_records)
            self._write_premium_report(premium_records)
            self._write_summary_report(dividend_records, interest_records, 
                                     stock_records, option_records)

        except Exception as e:
            self.logger.error(f"Report generation error: {e}", exc_info=True)
            raise

    def _write_dividend_report(self, dividend_records: List[DividendRecord]) -> None:
        """配当レポートの生成"""
        formatted_records = [self._format_dividend_record(r) for r in dividend_records]
        self.context.writers['dividend_csv'].output(formatted_records)
        self.context.writers['console'].output(dividend_records)

    def _write_interest_report(self, interest_records: List[InterestRecord]) -> None:
        """利子レポートの生成"""
        formatted_records = [self._format_interest_record(r) for r in interest_records]
        self.context.writers['interest_csv'].output(formatted_records)
        self.context.writers['console'].output(interest_records)

    def _write_stock_report(self, stock_records: List[StockTradeRecord]) -> None:
        """株式取引レポートの生成"""
        formatted_records = [self._format_stock_record(r) for r in stock_records]
        self.context.writers['stock_trade_csv'].output(formatted_records)

    def _write_option_report(self, option_records: List[OptionTradeRecord]) -> None:
        """オプション取引レポートの生成"""
        formatted_records = [self._format_option_record(r) for r in option_records]
        self.context.writers['option_trade_csv'].output(formatted_records)

    def _write_premium_report(self, premium_records: List[PremiumRecord]) -> None:
        """プレミアムレポートの生成"""
        formatted_records = [self._format_premium_record(r) for r in premium_records]
        self.context.writers['option_premium_csv'].output(formatted_records)

    def _format_premium_record(self, record: PremiumRecord) -> Dict:
        """プレミアム記録のフォーマット"""
        summary = self.context.premium_processor._transactions[record.symbol]
        trading_gain = (summary.sell_to_close_amount - summary.buy_to_close_amount)
        final_premium = (summary.sell_to_open_amount - summary.buy_to_open_amount +
                        trading_gain - summary.fees)

        return {
            'symbol': record.symbol,
            'expiry_date': record.expiry_date,
            'strike_price': record.strike_price,
            'option_type': record.option_type,
            'sell_to_open_total': summary.sell_to_open_amount,
            'buy_to_open_total': summary.buy_to_open_amount,
            'buy_to_close_total': summary.buy_to_close_amount,
            'sell_to_close_total': summary.sell_to_close_amount,
            'fees_total': summary.fees,
            'trading_gain': trading_gain,
            'final_premium': final_premium,
            'status': summary.status,
            'close_date': summary.close_date
        }

    def _format_dividend_record(self, record: DividendRecord) -> Dict:
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

    def _format_interest_record(self, record: InterestRecord) -> Dict:
        """利子記録のフォーマット"""
        return {
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol or '',
            'description': record.description,
            'type': record.income_type,
            'gross_amount': record.gross_amount.amount,
            'tax_amount': record.tax_amount.amount,
            'net_amount': record.gross_amount.amount - record.tax_amount.amount
        }

    def _format_stock_record(self, record: StockTradeRecord) -> Dict:
        """株式取引記録のフォーマット"""
        return {
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': 'Stock',
            'action': record.action,
            'quantity': record.quantity,
            'price': record.price.amount,
            'realized_gain': record.realized_gain.amount
        }

    def _format_option_record(self, record: OptionTradeRecord) -> Dict:
        """オプション取引記録のフォーマット"""
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
            'price': record.price.amount,
            'realized_gain': record.realized_gain.amount,
            'is_expired': record.is_expired
        }

    def _calculate_dividend_summary(self, 
                                    dividend_records: List, 
                                    interest_records: List) -> Dict:
        """配当・利子収入のサマリー計算"""
        summary = {
            'dividend_total': sum(r.gross_amount.amount for r in dividend_records),
            'interest_total': sum(r.gross_amount.amount for r in interest_records),
            'tax_total': sum(r.tax_amount.amount for r in dividend_records + interest_records)
        }
        
        summary['net_total'] = (
            summary['dividend_total'] +
            summary['interest_total'] -
            summary['tax_total']
        )
        
        return summary

    def _calculate_trading_summary(self, 
                                  stock_records: List,
                                  option_records: List) -> Dict:
        """取引損益のサマリー計算"""
        # 株式取引の損益
        stock_gain = sum(r.realized_gain.amount for r in stock_records)
        
        # オプション取引の損益（取引による損益）
        option_gain = sum(r.realized_gain.amount for r in option_records)
        
        # プレミアムの計算（確定損益）
        premium_gain = sum(
            summary.net_premium 
            for summary in self.context.premium_processor._transactions.values()
            if summary.is_closed and summary.status == 'EXPIRED'
        )
        
        summary = {
            'stock_gain': stock_gain,
            'option_gain': option_gain,
            'premium_income': premium_gain
        }
        
        summary['net_total'] = (
            summary['stock_gain'] +
            summary['option_gain'] +
            summary['premium_income']
        )
        
        return summary
        
    def _write_summary_report(self, dividend_records: List, 
                             interest_records: List,
                             stock_records: List,
                             option_records: List) -> None:
        """サマリーレポートの生成"""
        try:
            # 収入サマリーの計算
            income_summary = self._calculate_dividend_summary(
                dividend_records, 
                interest_records
            )
            
            # 取引損益の集計
            trading_summary = self._calculate_trading_summary(
                stock_records, option_records
            )
            
            # 全体のサマリーを作成
            total_summary = {
                'income': income_summary,
                'trading': trading_summary,
                'total': {
                    'total_income': income_summary['net_total'],
                    'total_trading': trading_summary['net_total'],
                    'grand_total': (
                        income_summary['net_total'] + 
                        trading_summary['net_total']
                    )
                }
            }

            # CSVへの出力
            self._write_summary_to_csv(income_summary, trading_summary)

            # 各出力先に書き出し
            self.context.display_outputs['summary_file'].output(total_summary)
            self.context.display_outputs['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            raise

    def _write_summary_to_csv(self, income_summary: Dict, trading_summary: Dict) -> None:
        """サマリーをCSVに出力"""
        summary_record = {
            'Account': 'ALL',
            'Dividend': income_summary['dividend_total'],
            'Interest': income_summary['interest_total'],
            'Tax': income_summary['tax_total'],
            'Net Total': (
                income_summary['dividend_total'] +
                income_summary['interest_total'] -
                income_summary['tax_total']
            )
        }
        self.context.writers['profit_loss_csv'].output([summary_record])