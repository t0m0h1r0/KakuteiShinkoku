from typing import Dict, Any
import logging

from .interfaces import BaseReportGenerator
from .dividend import DividendReportGenerator
from .interest import InterestReportGenerator
from .stock import StockTradeReportGenerator
from .option import OptionTradeReportGenerator
from .summary import FinalSummaryReportGenerator
from .calculators import ReportCalculator

class ReportManager:
    """投資レポート管理クラス"""
    
    def __init__(self, writers: Dict[str, Any]):
        self.writers = writers
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_generators()

    def _initialize_generators(self):
        """レポートジェネレータを初期化"""
        self.generators = {
            'dividend': DividendReportGenerator(self.writers['dividend_csv']),
            'interest': InterestReportGenerator(self.writers['interest_csv']),
            'stock_trade': StockTradeReportGenerator(self.writers['stock_trade_csv']),
            'option_trade': OptionTradeReportGenerator(self.writers['option_trade_csv']),
            'final_summary': FinalSummaryReportGenerator(self.writers['final_summary_csv'])
        }

    def generate_reports(self, data: Dict[str, Any]) -> None:
        """レポートの生成と出力"""
        try:
            # レポート生成と書き出し
            for name, generator in self.generators.items():
                try:
                    generator.generate_and_write(data)
                except Exception as e:
                    self.logger.error(f"{name.capitalize()}レポート生成失敗: {e}")
            
            # コンソール出力
            self._output_console_summary(data)

        except Exception as e:
            self.logger.error(f"全レポート生成中にエラー: {e}")
            raise

    def _output_console_summary(self, data: Dict[str, Any]) -> None:
        """コンソールに概要サマリーを出力"""
        try:
            # 収入サマリーの計算
            income_summary = ReportCalculator.calculate_income_summary(
                data.get('dividend_records', []), 
                data.get('interest_records', [])
            )
            
            # 各種取引のサマリー計算
            stock_summary = ReportCalculator.calculate_stock_summary_details(
                data.get('stock_records', [])
            )
            option_summary = ReportCalculator.calculate_option_summary_details(
                data.get('option_records', [])
            )
            
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
            self.logger.error(f"コンソール概要出力中にエラー: {e}")
            raise
