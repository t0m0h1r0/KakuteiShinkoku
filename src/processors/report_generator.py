from typing import Dict, List, Any
from decimal import Decimal
import logging
from abc import ABC, abstractmethod

from ..core.interfaces import IWriter
from ..app.context import ApplicationContext
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
                                     stock_records, option_records, premium_records)

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
            'type': record.action_type,
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
            'realized_gain': record.realized_gain.amount if hasattr(record, 'realized_gain') else 0
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
            'is_expired': record.is_expired
        }

    def _format_premium_record(self, record: PremiumRecord) -> Dict:
        """プレミアム記録のフォーマット"""
        return {
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'expiry_date': record.expiry_date,
            'strike_price': record.strike_price,
            'option_type': record.option_type,
            'premium_amount': record.premium_amount.amount
        }

    def _write_summary_report(self, dividend_records: List, 
                             interest_records: List,
                             stock_records: List,
                             option_records: List,
                             premium_records: List) -> None:
        """サマリーレポートの生成"""
        try:
            # 配当・利子収入の集計
            income_summary = self._calculate_dividend_summary(
                dividend_records, 
                interest_records
            )
            
            # 取引損益の集計
            trading_summary = self._calculate_trading_summary(
                stock_records, option_records, premium_records
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

            # 各出力先に書き出し
            self.context.display_outputs['summary_file'].output(total_summary)
            self.context.display_outputs['console'].output(total_summary)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            raise

    def _calculate_dividend_summary(self, 
                                  dividend_records: List, 
                                  interest_records: List) -> Dict:
        """配当・利子収入のサマリー計算"""
        # 利子の詳細カテゴリごとに集計
        interest_breakdown = {
            'cd_interest_total': Decimal('0'),
            'bond_interest_total': Decimal('0'),
            'bank_credit_interest_total': Decimal('0'),
            'other_interest_total': Decimal('0')
        }

        for record in interest_records:
            type_key = self._get_interest_total_key(record)
            interest_breakdown[type_key] += record.gross_amount.amount

        summary = {
            'dividend_total': sum(r.gross_amount.amount for r in dividend_records),
            'cd_interest_total': interest_breakdown['cd_interest_total'],
            'bond_interest_total': interest_breakdown['bond_interest_total'],
            'bank_credit_interest_total': interest_breakdown['bank_credit_interest_total'],
            'other_interest_total': interest_breakdown['other_interest_total'],
            'tax_total': sum(r.tax_amount.amount for r in dividend_records + interest_records)
        }
        
        summary['interest_total'] = sum([
            summary['cd_interest_total'],
            summary['bond_interest_total'],
            summary['bank_credit_interest_total'],
            summary['other_interest_total']
        ])

        summary['net_total'] = (
            summary['dividend_total'] +
            summary['interest_total'] -
            summary['tax_total']
        )
        
        return summary

    def _get_interest_total_key(self, record: InterestRecord) -> str:
        """利子の集計キーを取得"""
        action_type = record.action_type.upper()

        if action_type == 'CD INTEREST':
            return 'cd_interest_total'
        elif action_type == 'BOND INTEREST':
            return 'bond_interest_total'
        elif action_type == 'CREDIT INTEREST' or action_type == 'BANK INTEREST':
            return 'bank_credit_interest_total'
        else:
            return 'other_interest_total'

    def _calculate_trading_summary(self, 
                                  stock_records: List,
                                  option_records: List, 
                                  premium_records: List) -> Dict:
        """取引損益のサマリー計算"""
        summary = {
            'stock_gain': sum(r.realized_gain.amount for r in stock_records),
            'option_gain': sum(r.price.amount 
                             for r in option_records 
                             if r.action == 'SELL'),
            'premium_income': sum(r.premium_amount.amount 
                                for r in premium_records)
        }
        
        summary['net_total'] = (
            summary['stock_gain'] +
            summary['option_gain'] +
            summary['premium_income']
        )
        
        return summary