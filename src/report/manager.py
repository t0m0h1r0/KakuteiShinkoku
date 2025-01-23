from typing import Dict, Any
import logging

from .interfaces import ReportWriterInterface
from .generators import (
    DividendReportGenerator,
    InterestReportGenerator,
    StockTradeReportGenerator,
    OptionTradeReportGenerator,
    OptionSummaryReportGenerator,
    FinalSummaryReportGenerator
)
from .calculators import ReportCalculator

class InvestmentReportManager:
    """投資レポート管理クラス"""
    
    def __init__(self, writers: Dict[str, ReportWriterInterface]):
        self.writers = writers
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_reports(self, data: Dict[str, Any]) -> None:
        """レポートの生成と出力"""
        try:
            # 各レポートジェネレータを定義
            report_generators = {
                'dividend': DividendReportGenerator(self.writers['dividend_csv']),
                'interest': InterestReportGenerator(self.writers['interest_csv']),
                'stock_trade': StockTradeReportGenerator(self.writers['stock_trade_csv']),
                'option_trade': OptionTradeReportGenerator(self.writers['option_trade_csv']),
                'option_summary': OptionSummaryReportGenerator(self.writers['option_summary_csv']),
                'final_summary': FinalSummaryReportGenerator(self.writers['final_summary_csv'])
            }

            # レポート生成と書き出し
            for name, generator in report_generators.items():
                try:
                    generator.generate_and_write(data)
                except Exception as e:
                    self.logger.error(f"{name.capitalize()} report generation failed: {e}")
            
            # コンソール出力
            self._output_console_summary(data)

        except Exception as e:
            self.logger.error(f"全レポート生成中にエラーが発生: {e}")
            raise

    def _output_console_summary(self, data: Dict[str, Any]) -> None:
        """コンソールに概要サマリーを出力"""
        try:
            # 各収入・取引の集計
            dividend_records = data.get('dividend_records', [])
            interest_records = data.get('interest_records', [])
            stock_records = data.get('stock_records', [])
            option_records = data.get('option_records', [])

            # 収入サマリーの計算
            income_summary = ReportCalculator.calculate_income_summary(
                dividend_records, interest_records
            )
            
            # 各種取引のサマリー計算
            stock_summary = ReportCalculator.calculate_stock_summary_details(stock_records)
            option_summary = ReportCalculator.calculate_option_summary_details(option_records)
            
            # 総合計の計算
            total_summary = {
                'income': income_summary,
                'trading': {
                    'stock_gain': stock_summary,
                    'option_gain': option_summary['trading_pnl'],
                    'premium_income': option_summary['premium_pnl'],
                    'net_total': (
                        stock_summary +
                        option_summary['trading_pnl'] +
                        option_summary['premium_pnl']
                    )
                },
                'total': {
                    'total_income': income_summary['net_total'],
                    'total_trading': (
                        stock_summary +
                        option_summary['trading_pnl'] +
                        option_summary['premium_pnl']
                    ),
                    'grand_total': (
                        income_summary['net_total'] +
                        stock_summary +
                        option_summary['trading_pnl'] +
                        option_summary['premium_pnl']
                    )
                }
            }

            # コンソール出力
            self.writers['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"コンソール概要出力中にエラーが発生: {e}")
            raise