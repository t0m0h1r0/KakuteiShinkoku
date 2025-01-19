from typing import Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP
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

    def _format_dividend_record(self, record: DividendRecord) -> Dict:
        """配当記録のフォーマット"""
        net_amount = record.gross_amount.amount - record.tax_amount.amount
        net_amount_jpy = record.gross_amount_jpy.amount - record.tax_amount_jpy.amount
        
        return {
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.income_type,
            'gross_amount': record.gross_amount.amount,
            'tax_amount': record.tax_amount.amount,
            'net_amount': net_amount,
            'gross_amount_jpy': int(record.gross_amount_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'tax_amount_jpy': int(record.tax_amount_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'net_amount_jpy': int(net_amount_jpy.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'exchange_rate': record.exchange_rate
        }

    def _format_interest_record(self, record: InterestRecord) -> Dict:
        """利子記録のフォーマット"""
        net_amount = record.gross_amount.amount - record.tax_amount.amount
        net_amount_jpy = record.gross_amount_jpy.amount - record.tax_amount_jpy.amount
        
        return {
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol or '',
            'description': record.description,
            'action': record.action_type,
            'gross_amount': record.gross_amount.amount,
            'tax_amount': record.tax_amount.amount,
            'net_amount': net_amount,
            'gross_amount_jpy': int(record.gross_amount_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'tax_amount_jpy': int(record.tax_amount_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'net_amount_jpy': int(net_amount_jpy.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'exchange_rate': record.exchange_rate
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
            'realized_gain': record.realized_gain.amount,
            'price_jpy': int(record.price_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'realized_gain_jpy': int(record.realized_gain_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'exchange_rate': record.exchange_rate
        }

    def _format_option_record(self, record: OptionTradeRecord) -> Dict:
        """オプション取引記録のフォーマット"""
        return {
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'price': record.price.amount,
            'price_jpy': int(record.price_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'fees_jpy': int(record.fees_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'realized_gain_jpy': int(record.realized_gain_jpy.amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'exchange_rate': record.exchange_rate
        }

    def _format_premium_record(self, record: PremiumRecord) -> Dict:
        """プレミアム記録のフォーマット"""
        summary = self.context.premium_processor._transactions[record.symbol]
        final_premium = (summary.sell_to_open_amount - summary.buy_to_open_amount +
                        (summary.sell_to_close_amount - summary.buy_to_close_amount) - 
                        summary.fees)

        final_premium_jpy = final_premium * record.exchange_rate
        fees_total_jpy = summary.fees * record.exchange_rate

        return {
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'fees_total': summary.fees,
            'final_premium': final_premium,
            'status': summary.status,
            'close_date': summary.close_date,
            'final_premium_jpy': int(final_premium_jpy.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'fees_total_jpy': int(fees_total_jpy.quantize(Decimal('1'), rounding=ROUND_HALF_UP)),
            'exchange_rate': record.exchange_rate
        }

    def _calculate_dividend_summary(self, dividend_records: List, interest_records: List) -> Dict:
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

    def _calculate_trading_summary(self, stock_records: List, option_records: List) -> Dict:
        """取引損益のサマリー計算"""
        stock_gain = sum(r.realized_gain.amount for r in stock_records)
        
        option_gain = sum(
            summary.net_premium 
            for summary in self.context.premium_processor._transactions.values()
            if summary.is_closed and summary.status == 'CLOSED'
        )
        
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
        
    def _write_summary_report(self, dividend_records: List, interest_records: List,
                             stock_records: List, option_records: List) -> None:
        """サマリーレポートの生成"""
        try:
            income_summary = self._calculate_dividend_summary(
                dividend_records, interest_records
            )
            
            trading_summary = self._calculate_trading_summary(
                stock_records, option_records
            )
            
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

            self._write_summary_to_csv(income_summary, trading_summary)
            
            self.context.display_outputs['summary_file'].output(total_summary)
            self.context.display_outputs['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            raise

    def _write_summary_to_csv(self, income_summary: Dict, trading_summary: Dict) -> None:
        """サマリーをCSVに出力"""
        # USD金額の計算
        net_total = (
            income_summary['dividend_total'] +
            income_summary['interest_total'] -
            income_summary['tax_total']
        )
        
        # JPY金額の計算
        exchange_rate = self._get_latest_exchange_rate()
        dividend_jpy = (income_summary['dividend_total'] * exchange_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        interest_jpy = (income_summary['interest_total'] * exchange_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        tax_jpy = (income_summary['tax_total'] * exchange_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        net_total_jpy = (net_total * exchange_rate).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

        summary_record = {
            'Account': 'ALL',
            'Dividend': income_summary['dividend_total'],
            'Interest': income_summary['interest_total'],
            'Tax': income_summary['tax_total'],
            'Net Total': net_total,
            'Dividend_JPY': int(dividend_jpy),
            'Interest_JPY': int(interest_jpy),
            'Tax_JPY': int(tax_jpy),
            'Net Total_JPY': int(net_total_jpy),
            'Exchange Rate': exchange_rate
        }
        self.context.writers['profit_loss_csv'].output([summary_record])

    def _get_latest_exchange_rate(self) -> Decimal:
        """最新の為替レートを取得"""
        all_records = (
            self.context.processing_results.get('dividend_records', []) +
            self.context.processing_results.get('interest_records', []) +
            self.context.processing_results.get('stock_records', []) +
            self.context.processing_results.get('option_records', [])
        )
        
        if not all_records:
            return Decimal('150.0')  # デフォルトレート
        
        latest_record = max(
            all_records,
            key=lambda x: x.record_date if hasattr(x, 'record_date') else x.trade_date
        )
        
        return latest_record.exchange_rate