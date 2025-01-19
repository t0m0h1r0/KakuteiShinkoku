from typing import Dict, List, Any
from decimal import Decimal, ROUND_HALF_UP
import logging
from datetime import datetime
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
            
            # 最終サマリーレポートの生成を追加
            self._write_final_summary(dividend_records, interest_records,
                                    stock_records, option_records,
                                    premium_records)

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

    def _write_final_summary(self, dividend_records: List[DividendRecord],
                           interest_records: List[InterestRecord],
                           stock_records: List[StockTradeRecord],
                           option_records: List[OptionTradeRecord],
                           premium_records: List[PremiumRecord]) -> None:
        """最終サマリーレポートの生成（テーブル形式）"""
        try:
            # 各サマリーの計算
            dividend_summary = self._calculate_dividend_final_summary(dividend_records)
            interest_summary = self._calculate_interest_final_summary(interest_records)
            stock_summary = self._calculate_stock_final_summary(stock_records)
            option_summary = self._calculate_option_final_summary(option_records)
            premium_summary = self._calculate_premium_final_summary(premium_records)
            
            # 配当の税額計算
            dividend_tax_usd = sum(r.tax_amount.amount for r in dividend_records)
            dividend_tax_jpy = sum(r.tax_amount_jpy.amount for r in dividend_records)

            # 合計の計算
            total_usd = (
                dividend_summary['total_usd'] +
                interest_summary['total_usd'] +
                stock_summary['total_usd'] +
                option_summary['total_usd'] +
                premium_summary['total_usd']
            )
            total_jpy = (
                dividend_summary['total_jpy'] +
                interest_summary['total_jpy'] +
                stock_summary['total_jpy'] +
                option_summary['total_jpy'] +
                premium_summary['total_jpy']
            )

            # USD金額は小数第二位、JPY金額は整数に丸める
            def format_usd(amount: Decimal) -> Decimal:
                return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            def format_jpy(amount: Decimal) -> Decimal:
                return amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

            # テーブル形式でデータを作成
            final_summary = [
                {
                    'item': 'Dividend Income',
                    'usd': format_usd(dividend_summary['total_usd']),
                    'jpy': format_jpy(dividend_summary['total_jpy'])
                },
                {
                    'item': 'Dividend Withholding Tax',
                    'usd': format_usd(dividend_tax_usd),
                    'jpy': format_jpy(dividend_tax_jpy)
                },
                {
                    'item': 'Interest Income',
                    'usd': format_usd(interest_summary['total_usd']),
                    'jpy': format_jpy(interest_summary['total_jpy'])
                },
                {
                    'item': 'Stock Trading Gains',
                    'usd': format_usd(stock_summary['total_usd']),
                    'jpy': format_jpy(stock_summary['total_jpy'])
                },
                {
                    'item': 'Option Trading Gains',
                    'usd': format_usd(option_summary['total_usd']),
                    'jpy': format_jpy(option_summary['total_jpy'])
                },
                {
                    'item': 'Option Premium Income',
                    'usd': format_usd(premium_summary['total_usd']),
                    'jpy': format_jpy(premium_summary['total_jpy'])
                },
                {
                    'item': 'Total',
                    'usd': format_usd(total_usd),
                    'jpy': format_jpy(total_jpy)
                }
            ]

            # CSVに出力
            self.context.writers['final_summary'].output(final_summary)

            # コンソールにも出力
            self.context.display_outputs['console'].output({
                'type': 'final_summary',
                'data': final_summary
            })

        except Exception as e:
            self.logger.error(f"Error generating final summary: {e}")
            raise

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

            self.context.display_outputs['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
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

    def _calculate_trading_summary(self, stock_records: List,
                                 option_records: List) -> Dict:
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

    def _calculate_dividend_final_summary(self, records: List[DividendRecord]) -> Dict:
        """配当収入の最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')

        for record in records:
            # 税引後の金額を計算
            total_usd += record.gross_amount.amount - record.tax_amount.amount
            total_jpy += (record.gross_amount_jpy.amount - record.tax_amount_jpy.amount)

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy
        }

    def _calculate_interest_final_summary(self, records: List[InterestRecord]) -> Dict:
        """利子収入の最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')

        for record in records:
            # 税引後の金額を計算
            total_usd += record.gross_amount.amount - record.tax_amount.amount
            total_jpy += (record.gross_amount_jpy.amount - record.tax_amount_jpy.amount)

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy
        }

    def _calculate_stock_final_summary(self, records: List[StockTradeRecord]) -> Dict:
        """株式取引の最終サマリー計算"""
        total_usd = sum(r.realized_gain.amount for r in records)
        total_jpy = sum(r.realized_gain_jpy.amount for r in records)

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy
        }

    def _calculate_option_final_summary(self, records: List[OptionTradeRecord]) -> Dict:
        """オプション取引の最終サマリー計算"""
        total_usd = sum(r.realized_gain.amount for r in records)
        total_jpy = sum(r.realized_gain_jpy.amount for r in records)

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy
        }

    def _calculate_premium_final_summary(self, records: List[PremiumRecord]) -> Dict:
        """オプションプレミアムの最終サマリー計算"""
        total_usd = Decimal('0')
        total_jpy = Decimal('0')

        for record in records:
            if record.premium_amount:
                total_usd += record.premium_amount.amount
            if record.premium_amount_jpy:
                total_jpy += record.premium_amount_jpy.amount

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy
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
            'price': record.price.amount,
            'price_jpy': int(record.price_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'fees_jpy': int(record.fees_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'realized_gain_jpy': int(record.realized_gain_jpy.amount.quantize(
                Decimal('1'), rounding=ROUND_HALF_UP
            )),
            'exchange_rate': record.exchange_rate
        }

    def _format_premium_record(self, record: PremiumRecord) -> Dict:
        """プレミアム記録のフォーマット"""
        summary = self.context.premium_processor._transactions[record.symbol]
        
        # プレミアム収入（売り建て時の受取プレミアム - 買い建て時の支払いプレミアム）
        premium_income = summary.sell_to_open_amount - summary.buy_to_open_amount
        
        # 譲渡損益（売り決済時の受取プレミアム - 買い決済時の支払いプレミアム）
        trading_gains = summary.sell_to_close_amount - summary.buy_to_close_amount
        
        # 手数料を比率で按分
        total_amount = abs(premium_income) + abs(trading_gains)
        if total_amount != 0:
            premium_fees = summary.fees * (abs(premium_income) / total_amount)
            trading_fees = summary.fees * (abs(trading_gains) / total_amount)
        else:
            premium_fees = trading_fees = Decimal('0')
        
        # 純利益の計算（USD）
        net_premium_income = (premium_income - premium_fees).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_trading_gains = (trading_gains - trading_fees).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        fees_total = summary.fees.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # JPY換算（整数に丸め）
        premium_income_jpy = (net_premium_income * record.exchange_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP)
        trading_gains_jpy = (net_trading_gains * record.exchange_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP)
        fees_total_jpy = (summary.fees * record.exchange_rate).quantize(
            Decimal('1'), rounding=ROUND_HALF_UP)

        return {
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'fees_total': fees_total,
            'premium_income': net_premium_income,
            'trading_gains': net_trading_gains,
            'status': summary.status,
            'close_date': summary.close_date,
            'premium_income_jpy': premium_income_jpy,
            'trading_gains_jpy': trading_gains_jpy,
            'fees_total_jpy': fees_total_jpy,
            'exchange_rate': record.exchange_rate
        }