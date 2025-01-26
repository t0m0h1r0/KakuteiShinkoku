from typing import Dict, Any, List
import logging

from ..report.calculators import ReportCalculator
from ..report.dividend import DividendReportGenerator
from ..report.interest import InterestReportGenerator
from ..report.stock import StockTradeReportGenerator
from ..report.option import OptionTradeReportGenerator
from ..report.summary import FinalSummaryReportGenerator, OptionSummaryReportGenerator

class InvestmentReporter:
    def __init__(self, writers):
        self.writers = writers
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize_generators()

    def _initialize_generators(self):
        self.generators = {
            'dividend': DividendReportGenerator(self.writers['dividend_csv']),
            'interest': InterestReportGenerator(self.writers['interest_csv']),
            'stock_trade': StockTradeReportGenerator(self.writers['stock_trade_csv']),
            'option_trade': OptionTradeReportGenerator(self.writers['option_trade_csv']),
            'option_summary': OptionSummaryReportGenerator(self.writers['option_summary_csv']),
            'final_summary': FinalSummaryReportGenerator(self.writers['final_summary_csv'])
        }

    def generate_reports(self, data: Dict[str, Any]) -> bool:
        try:
            self._generate_detail_reports(data)
            self._output_console_summary(data)
            return True
        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            return False

    def _generate_detail_reports(self, data: Dict[str, Any]):
        for name, generator in self.generators.items():
            try:
                generator.generate_and_write(data)
            except Exception as e:
                self.logger.error(f"{name}レポート生成エラー: {e}")

    def _output_console_summary(self, data: Dict[str, Any]):
        income_summary = self._calculate_income_summary(data)
        trading_summary = self._calculate_trading_summary(data)
        total_summary = self._calculate_total_summary(income_summary, trading_summary)

        summary = {
            'income': income_summary,
            'trading': trading_summary,
            'total': total_summary
        }
        
        self.writers['console'].output(summary)

    def _calculate_income_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        calculator = ReportCalculator()
        return calculator.calculate_income_summary(
            data.get('dividend_records', []),
            data.get('interest_records', [])
        )

    def _calculate_trading_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        calculator = ReportCalculator()
        stock_summary = calculator.calculate_stock_summary_details(data.get('stock_records', []))
        option_summary = calculator.calculate_option_summary_details(data.get('option_records', []))
        
        return {
            'stock_gain': stock_summary,
            'option_gain': option_summary['trading_pnl'],
            'premium_income': option_summary['premium_pnl'],
            'net_total': stock_summary + option_summary['trading_pnl'] + option_summary['premium_pnl']
        }

    def _calculate_total_summary(self, income_summary: Dict[str, Any], trading_summary: Dict[str, Any]) -> Dict[str, Any]:
        net_income = income_summary['dividend_total'] + income_summary['interest_total'] - income_summary['tax_total']
        return {
            'total_income': net_income,
            'total_trading': trading_summary['net_total'],
            'grand_total': net_income + trading_summary['net_total']
        }