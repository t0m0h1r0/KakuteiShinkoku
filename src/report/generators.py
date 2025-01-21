from typing import Dict, Any, List
from decimal import Decimal

from .interfaces import BaseReportGenerator
from .calculators import ReportCalculator

class DividendReportGenerator(BaseReportGenerator):
    """配当レポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """配当レポートを生成"""
        dividend_records = data.get('dividend_records', [])
        
        return [
            {
                'date': record.record_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'type': record.income_type,
                'gross_amount': record.gross_amount.amount,
                'tax_amount': record.tax_amount.amount,
                'net_amount': record.gross_amount.amount - record.tax_amount.amount,
                'gross_amount_jpy': int(record.gross_amount_jpy.amount),
                'tax_amount_jpy': int(record.tax_amount_jpy.amount),
                'net_amount_jpy': int(record.gross_amount_jpy.amount - record.tax_amount_jpy.amount),
                'exchange_rate': record.exchange_rate
            }
            for record in dividend_records
        ]

class InterestReportGenerator(BaseReportGenerator):
    """利子レポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """利子レポートを生成"""
        interest_records = data.get('interest_records', [])
        
        return [
            {
                'date': record.record_date,
                'account': record.account_id,
                'symbol': record.symbol or '',
                'description': record.description,
                'action': record.action_type,
                'gross_amount': record.gross_amount.amount,
                'tax_amount': record.tax_amount.amount,
                'net_amount': record.gross_amount.amount - record.tax_amount.amount,
                'gross_amount_jpy': int(record.gross_amount_jpy.amount),
                'tax_amount_jpy': int(record.tax_amount_jpy.amount),
                'net_amount_jpy': int(record.gross_amount_jpy.amount - record.tax_amount_jpy.amount),
                'exchange_rate': record.exchange_rate
            }
            for record in interest_records
        ]

class StockTradeReportGenerator(BaseReportGenerator):
    """株式取引レポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """株式取引レポートを生成"""
        stock_records = data.get('stock_records', [])
        
        return [
            {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'action': record.action,
                'quantity': record.quantity,
                'price': record.price.amount,
                'realized_gain': record.realized_gain.amount,
                'price_jpy': int(record.price_jpy.amount),
                'realized_gain_jpy': int(record.realized_gain_jpy.amount),
                'exchange_rate': record.exchange_rate
            }
            for record in stock_records
        ]

class OptionTradeReportGenerator(BaseReportGenerator):
    """オプション取引レポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """オプション取引レポートを生成"""
        option_records = data.get('option_records', [])
        
        return [
            {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'action': record.action,
                'quantity': record.quantity,
                'option_type': record.option_type,
                'strike_price': float(record.strike_price),
                'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
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
            for record in option_records
        ]

class OptionSummaryReportGenerator(BaseReportGenerator):
    """オプション取引サマリーレポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """オプション取引サマリーレポートを生成"""
        option_summary_records = self._get_option_summary_records(data)
        
        return [
            {
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'underlying': record.underlying,
                'option_type': record.option_type,
                'strike_price': float(record.strike_price),
                'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
                'open_date': record.open_date.strftime('%Y-%m-%d'),
                'close_date': record.close_date.strftime('%Y-%m-%d') if record.close_date else '',
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
            for record in option_summary_records
        ]
    
    def _get_option_summary_records(self, data: Dict[str, Any]) -> List:
        """オプションサマリーレコードを取得"""
        from ..processors.option_processor import OptionProcessor
        option_processor = data.get('option_processor')
        
        if option_processor and isinstance(option_processor, OptionProcessor):
            return option_processor.get_summary_records()
        
        return data.get('option_summary_records', [])

class FinalSummaryReportGenerator(BaseReportGenerator):
    """最終サマリーレポート生成クラス"""
    
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """最終サマリーレポートを生成"""
        dividend_records = data.get('dividend_records', [])
        interest_records = data.get('interest_records', [])
        stock_records = data.get('stock_records', [])
        option_records = data.get('option_records', [])
        
        # 各カテゴリの合計を計算
        dividend_tax_usd = sum(r.tax_amount.amount for r in dividend_records)
        dividend_tax_jpy = sum(r.tax_amount_jpy.amount for r in dividend_records)
        
        dividend_summary = ReportCalculator.calculate_income_summary_details(dividend_records)
        interest_summary = ReportCalculator.calculate_income_summary_details(interest_records)
        stock_summary = ReportCalculator.calculate_stock_summary_details(stock_records)
        option_summary = ReportCalculator.calculate_option_summary_details(option_records)
        
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

        # オプション取引 (譲渡損益)
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

        # オプション取引 (プレミアム収益)
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

        return summary_records