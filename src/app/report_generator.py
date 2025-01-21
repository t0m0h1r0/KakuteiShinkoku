from typing import Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP
import logging
from datetime import datetime
from abc import ABC, abstractmethod

from ..core.interfaces import IWriter
from ..app.application_context import ApplicationContext
from ..processors.trade_records import StockTradeRecord
from ..processors.option_records import OptionTradeRecord, OptionSummaryRecord
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

            # 各種レポートの生成
            self._write_dividend_report(dividend_records)
            self._write_interest_report(interest_records)
            self._write_stock_report(stock_records)
            self._write_option_report(option_records)  # オプション取引レポート
            self._write_summary_report(dividend_records, interest_records, 
                                     stock_records, option_records)
            
            # 最終サマリーレポートの生成
            self._write_final_summary(
                dividend_records=dividend_records,
                interest_records=interest_records,
                stock_records=stock_records,
                option_records=option_records
            )

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

        # サマリーレコードも出力
        if option_records:
            summary_records = self.context.option_processor.get_summary_records()
            formatted_summaries = [self._format_option_summary(r) for r in summary_records]
            self.context.writers['option_summary_csv'].output(formatted_summaries)

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

            self.context.writers['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            raise

    def _write_final_summary(self, 
                           dividend_records: List[DividendRecord],
                           interest_records: List[InterestRecord],
                           stock_records: List[StockTradeRecord],
                           option_records: List[OptionTradeRecord]) -> None:
        """最終サマリーレポートの生成（テーブル形式）"""
        try:
            # 各サマリーの計算
            dividend_summary = self._calculate_dividend_final_summary(dividend_records)
            interest_summary = self._calculate_interest_final_summary(interest_records)
            stock_summary = self._calculate_stock_final_summary(stock_records)
            option_summary = self._calculate_option_final_summary(option_records)
            
            # 配当の税額計算
            dividend_tax_usd = sum(r.tax_amount.amount for r in dividend_records)
            dividend_tax_jpy = sum(r.tax_amount_jpy.amount for r in dividend_records)

            # 各カテゴリの記録を作成
            summary_records = []
            
            # 配当
            summary_records.append({
                'category': 'Dividend Income',
                'subcategory': 'Gross Income',
                'gross_amount_usd': dividend_summary['total_usd'],
                'tax_amount_usd': dividend_tax_usd,
                'net_amount_usd': dividend_summary['total_usd'] - dividend_tax_usd,
                'gross_amount_jpy': dividend_summary['total_jpy'],
                'tax_amount_jpy': dividend_tax_jpy,
                'net_amount_jpy': dividend_summary['total_jpy'] - dividend_tax_jpy,
                'average_exchange_rate': dividend_summary.get('exchange_rate', Decimal('150.0'))
            })

            # 利子
            summary_records.append({
                'category': 'Interest Income',
                'subcategory': 'Gross Income',
                'gross_amount_usd': interest_summary['total_usd'],
                'tax_amount_usd': Decimal('0'),
                'net_amount_usd': interest_summary['total_usd'],
                'gross_amount_jpy': interest_summary['total_jpy'],
                'tax_amount_jpy': Decimal('0'),
                'net_amount_jpy': interest_summary['total_jpy'],
                'average_exchange_rate': interest_summary.get('exchange_rate', Decimal('150.0'))
            })

            # 株式取引
            summary_records.append({
                'category': 'Stock Trading',
                'subcategory': 'Trading Gain/Loss',
                'gross_amount_usd': stock_summary['total_usd'],
                'tax_amount_usd': Decimal('0'),
                'net_amount_usd': stock_summary['total_usd'],
                'gross_amount_jpy': stock_summary['total_jpy'],
                'tax_amount_jpy': Decimal('0'),
                'net_amount_jpy': stock_summary['total_jpy'],
                'average_exchange_rate': stock_summary.get('exchange_rate', Decimal('150.0'))
            })

            # オプション取引
            summary_records.append({
                'category': 'Option Trading',
                'subcategory': 'Trading Gain/Loss',
                'gross_amount_usd': option_summary['total_trading_pnl_usd'],
                'tax_amount_usd': Decimal('0'),
                'net_amount_usd': option_summary['total_trading_pnl_usd'],
                'gross_amount_jpy': option_summary['total_trading_pnl_jpy'],
                'tax_amount_jpy': Decimal('0'),
                'net_amount_jpy': option_summary['total_trading_pnl_jpy'],
                'average_exchange_rate': option_summary['weighted_exchange_rate']
            })

            summary_records.append({
                'category': 'Option Trading',
                'subcategory': 'Premium Income',
                'gross_amount_usd': option_summary['total_premium_pnl_usd'],
                'tax_amount_usd': option_summary['total_fees_usd'],
                'net_amount_usd': option_summary['total_premium_pnl_usd'] - option_summary['total_fees_usd'],
                'gross_amount_jpy': option_summary['total_premium_pnl_jpy'],
                'tax_amount_jpy': option_summary['total_fees_jpy'],
                'net_amount_jpy': option_summary['total_premium_pnl_jpy'] - option_summary['total_fees_jpy'],
                'average_exchange_rate': option_summary['weighted_exchange_rate']
            })

            # 最終サマリーの出力
            self.context.writers['final_summary_csv'].output(summary_records)

            # コンソールにも出力
            self.context.display_outputs['console'].output({
                'type': 'final_summary',
                'data': summary_records
            })

        except Exception as e:
            self.logger.error(f"Error generating final summary: {e}")
            raise

    def _calculate_dividend_summary(self, dividend_records: List,
                                  interest_records: List) -> Dict:
        """配当・利子収入のサマリー計算"""
        summary = {
            'dividend_total': sum(r.gross_amount.amount for r in dividend_records),
            'interest_total': sum(r.gross_amount.amount for r in interest_records),
            'tax_total': sum(r.tax_amount.amount 
                           for r in dividend_records + interest_records)
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
        
        option_trading_gain = sum(r.trading_pnl.amount for r in option_records)
        option_premium_gain = sum(r.premium_pnl.amount for r in option_records)
        
        summary = {
            'stock_gain': stock_gain,
            'option_gain': option_trading_gain,
            'premium_income': option_premium_gain
        }
        
        summary['net_total'] = (
            summary['stock_gain'] +
            summary['option_gain'] +
            summary['premium_income']
        )
        
        return summary

    def _calculate_dividend_final_summary(self, records: List[DividendRecord]) -> Dict:
        """配当収入の最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            # 税引後の金額を計算
            total_usd += record.gross_amount.amount - record.tax_amount.amount
            total_jpy += (record.gross_amount_jpy.amount - record.tax_amount_jpy.amount)
            exchange_rate_sum += record.exchange_rate
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
            'exchange_rate': exchange_rate_sum / count if count > 0 else Decimal('150.0')
        }

    def _calculate_interest_final_summary(self, records: List[InterestRecord]) -> Dict:
        """利子収入の最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            # 税引後の金額を計算
            total_usd += record.gross_amount.amount - record.tax_amount.amount
            total_jpy += (record.gross_amount_jpy.amount - record.tax_amount_jpy.amount)
            exchange_rate_sum += record.exchange_rate
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
            'exchange_rate': exchange_rate_sum / count if count > 0 else Decimal('150.0')
        }

    def _calculate_stock_final_summary(self, records: List[StockTradeRecord]) -> Dict:
        """株式取引の最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            total_usd += record.realized_gain.amount
            total_jpy += record.realized_gain_jpy.amount
            exchange_rate_sum += record.exchange_rate
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
            'exchange_rate': exchange_rate_sum / count if count > 0 else Decimal('150.0')
        }

    def _calculate_option_final_summary(self, records: List[OptionTradeRecord]) -> Dict:
        """オプション取引の最終サマリー計算"""
        total_trading_usd = Decimal('0')
        total_trading_jpy = Decimal('0')
        total_premium_usd = Decimal('0')
        total_premium_jpy = Decimal('0')
        total_fees_usd = Decimal('0')
        total_fees_jpy = Decimal('0')
        
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            total_trading_usd += record.trading_pnl.amount
            total_trading_jpy += record.trading_pnl_jpy.amount
            total_premium_usd += record.premium_pnl.amount
            total_premium_jpy += record.premium_pnl_jpy.amount
            total_fees_usd += record.fees.amount
            total_fees_jpy += record.fees_jpy.amount
            exchange_rate_sum += record.exchange_rate
            count += 1

        return {
            'total_trading_pnl_usd': total_trading_usd,
            'total_trading_pnl_jpy': total_trading_jpy,
            'total_premium_pnl_usd': total_premium_usd,
            'total_premium_pnl_jpy': total_premium_jpy,
            'total_fees_usd': total_fees_usd,
            'total_fees_jpy': total_fees_jpy,
            'weighted_exchange_rate': exchange_rate_sum / count if count > 0 else Decimal('150.0')
        }

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
            'gross_amount_jpy': int(record.gross_amount_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'tax_amount_jpy': int(record.tax_amount_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'net_amount_jpy': int(net_amount_jpy.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
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
            'gross_amount_jpy': int(record.gross_amount_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'tax_amount_jpy': int(record.tax_amount_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'net_amount_jpy': int(net_amount_jpy.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'exchange_rate': record.exchange_rate
        }

    def _format_stock_record(self, record: StockTradeRecord) -> Dict:
        """株式取引記録のフォーマット"""
        return {
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'price': record.price.amount,
            'realized_gain': record.realized_gain.amount,
            'price_jpy': int(record.price_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'realized_gain_jpy': int(record.realized_gain_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
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
            'option_type': record.option_type,
            'strike_price': record.strike_price,
            'expiry_date': record.expiry_date,
            'underlying': record.underlying,
            'price': float(record.price.amount),
            'fees': float(record.fees.amount),
            'trading_pnl': float(record.trading_pnl.amount),
            'premium_pnl': float(record.premium_pnl.amount),
            'price_jpy': int(record.price_jpy.amount),
            'fees_jpy': int(record.fees_jpy.amount),
            'trading_pnl_jpy': int(record.trading_pnl_jpy.amount),
            'premium_pnl_jpy': int(record.premium_pnl_jpy.amount),
            'exchange_rate': float(record.exchange_rate),
            'position_type': record.position_type,
            'is_closed': record.is_closed,
            'is_expired': record.is_expired
        }

    def _format_option_summary(self, record: OptionSummaryRecord) -> Dict:
        """オプション取引サマリー記録のフォーマット"""
        return {
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'underlying': record.underlying,
            'option_type': record.option_type,
            'strike_price': float(record.strike_price),
            'expiry_date': record.expiry_date,
            'open_date': record.open_date,
            'close_date': record.close_date or '',
            'status': record.status,
            'initial_quantity': int(record.initial_quantity),
            'remaining_quantity': int(record.remaining_quantity),
            'trading_pnl': float(record.trading_pnl.amount),
            'premium_pnl': float(record.premium_pnl.amount),
            'total_fees': float(record.total_fees.amount),
            'trading_pnl_jpy': int(record.trading_pnl_jpy.amount),
            'premium_pnl_jpy': int(record.premium_pnl_jpy.amount),
            'total_fees_jpy': int(record.total_fees_jpy.amount),
            'exchange_rate': float(record.exchange_rate)
        }