from typing import Dict, Any, List
from decimal import Decimal

from .interfaces import BaseReportGenerator
from .calculators import ReportCalculator
from ..exchange.money import Money
from ..exchange.currency import Currency

class DividendReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        dividend_records = data.get('dividend_records', [])
        
        return [{
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action_type,
            'gross_amount': record.gross_amount.usd,
            'tax_amount': record.tax_amount.usd,
            'net_amount': record.net_amount.usd,
            'gross_amount_jpy': record.gross_amount.jpy,
            'tax_amount_jpy': record.tax_amount.jpy,
            'net_amount_jpy': record.net_amount.jpy,
            'exchange_rate': record.exchange_rate
        } for record in dividend_records]

class InterestReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        interest_records = data.get('interest_records', [])
        
        return [{
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol or '',
            'description': record.description,
            'action': record.action_type,
            'gross_amount': record.gross_amount.usd,
            'tax_amount': record.tax_amount.usd,
            'net_amount': record.net_amount.usd,
            'gross_amount_jpy': record.gross_amount.jpy,
            'tax_amount_jpy': record.tax_amount.jpy,
            'net_amount_jpy': record.net_amount.jpy,
            'exchange_rate': record.exchange_rate
        } for record in interest_records]

class StockTradeReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        stock_records = data.get('stock_records', [])
        
        return [{
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'price': record.price.usd,
            'realized_gain': record.realized_gain.usd,
            'price_jpy': record.price.jpy,
            'realized_gain_jpy': record.realized_gain.jpy,
            'exchange_rate': record.exchange_rate
        } for record in stock_records]

class OptionTradeReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        option_records = data.get('option_records', [])
        
        return [{
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'option_type': record.option_type,
            'strike_price': float(record.strike_price),
            'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
            'underlying': record.underlying,
            'price': record.price.usd,
            'fees': record.fees.usd,
            'trading_pnl': record.trading_pnl.usd,
            'premium_pnl': record.premium_pnl.usd,
            'price_jpy': record.price.jpy,
            'fees_jpy': record.fees.jpy,
            'trading_pnl_jpy': record.trading_pnl.jpy,
            'premium_pnl_jpy': record.premium_pnl.jpy,
            'exchange_rate': record.exchange_rate,
            'position_type': record.position_type,
            'is_closed': record.is_closed,
            'is_expired': record.is_expired,
            'is_assigned': record.is_assigned
        } for record in option_records]

class OptionSummaryReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        option_summary_records = self._get_option_summary_records(data)
        
        return [{
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
            'initial_quantity': record.initial_quantity,
            'remaining_quantity': record.remaining_quantity,
            'trading_pnl': record.trading_pnl.usd,
            'premium_pnl': record.premium_pnl.usd,
            'total_fees': record.total_fees.usd,
            'trading_pnl_jpy': record.trading_pnl.jpy,
            'premium_pnl_jpy': record.premium_pnl.jpy,
            'total_fees_jpy': record.total_fees.jpy,
        } for record in option_summary_records]

    def _get_option_summary_records(self, data: Dict[str, Any]) -> List:
        from ..processors.option.processor import OptionProcessor
        option_processor = data.get('option_processor')
        
        if option_processor and isinstance(option_processor, OptionProcessor):
            return option_processor.get_summary_records()
        return data.get('option_summary_records', [])

class FinalSummaryReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        calculator = ReportCalculator()
        
        # 収入サマリーの計算
        dividend_records = data.get('dividend_records', [])
        interest_records = data.get('interest_records', [])
        
        # 収入サマリーの計算
        income_summary = calculator.calculate_income_summary(dividend_records, interest_records)
        
        # 株式とオプションの取引サマリーの計算
        stock_records = data.get('stock_records', [])
        option_records = data.get('option_records', [])
        
        # 株式取引のサマリー
        stock_summary = calculator.calculate_stock_summary_details(stock_records)
        
        # オプション取引のサマリー
        option_summary = calculator.calculate_option_summary_details(option_records)
        
        summary_records = []
        
        # 配当収入のサマリー
        summary_records.append({
            'category': '配当収入',
            'subcategory': '受取配当金',
            'gross_amount_usd': income_summary['dividend_total'].usd,
            'tax_amount_usd': income_summary.get('dividend_tax', income_summary['tax_total']).usd,
            'net_amount_usd': (income_summary['dividend_total'] - income_summary.get('dividend_tax', income_summary['tax_total'])).usd,
            'gross_amount_jpy': income_summary['dividend_total'].jpy,
            'tax_amount_jpy': income_summary.get('dividend_tax', income_summary['tax_total']).jpy,
            'net_amount_jpy': (income_summary['dividend_total'] - income_summary.get('dividend_tax', income_summary['tax_total'])).jpy,
        })
        
        # 利子収入のサマリー
        summary_records.append({
            'category': '利子収入',
            'subcategory': '受取利子',
            'gross_amount_usd': income_summary['interest_total'].usd,
            'tax_amount_usd': income_summary.get('interest_tax', Money(0, Currency.USD)).usd,
            'net_amount_usd': (income_summary['interest_total'] - income_summary.get('interest_tax', Money(0, Currency.USD))).usd,
            'gross_amount_jpy': income_summary['interest_total'].jpy,
            'tax_amount_jpy': income_summary.get('interest_tax', Money(0, Currency.USD)).jpy,
            'net_amount_jpy': (income_summary['interest_total'] - income_summary.get('interest_tax', Money(0, Currency.USD))).jpy,
        })
        
        # 株式取引のサマリー
        summary_records.append({
            'category': '株式取引',
            'subcategory': '売買損益',
            'gross_amount_usd': stock_summary.usd,
            'tax_amount_usd': Decimal('0'),
            'net_amount_usd': stock_summary.usd,
            'gross_amount_jpy': stock_summary.jpy,
            'tax_amount_jpy': Decimal('0'),
            'net_amount_jpy': stock_summary.jpy,
        })
        
        # オプション取引損益のサマリー
        summary_records.append({
            'category': 'オプション取引',
            'subcategory': '取引損益',
            'gross_amount_usd': option_summary['trading_pnl'].usd,
            'tax_amount_usd': Decimal('0'),
            'net_amount_usd': option_summary['trading_pnl'].usd,
            'gross_amount_jpy': option_summary['trading_pnl'].jpy,
            'tax_amount_jpy': Decimal('0'),
            'net_amount_jpy': option_summary['trading_pnl'].jpy,
        })
        
        # オプションプレミアム収入のサマリー
        summary_records.append({
            'category': 'オプション取引',
            'subcategory': 'プレミアム収入',
            'gross_amount_usd': option_summary['premium_pnl'].usd,
            'tax_amount_usd': Decimal('0'),
            'net_amount_usd': option_summary['premium_pnl'].usd,
            'gross_amount_jpy': option_summary['premium_pnl'].jpy,
            'tax_amount_jpy': Decimal('0'),
            'net_amount_jpy': option_summary['premium_pnl'].jpy,
        })
        
        return summary_records