from typing import Dict, Any, List, Tuple
from decimal import Decimal

from .interfaces import BaseReportGenerator
from .calculators import ReportCalculator

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
            'net_amount': record.gross_amount.usd - record.tax_amount.usd,
            'gross_amount_jpy': record.gross_amount_jpy.jpy,
            'tax_amount_jpy': record.tax_amount_jpy.jpy,
            'net_amount_jpy': record.gross_amount_jpy.jpy - record.tax_amount_jpy.jpy,
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
            'net_amount': record.gross_amount.usd - record.tax_amount.usd,
            'gross_amount_jpy': record.gross_amount_jpy.jpy,
            'tax_amount_jpy': record.tax_amount_jpy.jpy,
            'net_amount_jpy': record.gross_amount_jpy.jpy - record.tax_amount_jpy.jpy,
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
            'price_jpy': record.price_jpy.jpy,
            'realized_gain_jpy': record.realized_gain_jpy.jpy,
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
            'price_jpy': record.price_jpy.jpy,
            'fees_jpy': record.fees_jpy.jpy,
            'trading_pnl_jpy': record.trading_pnl_jpy.jpy,
            'premium_pnl_jpy': record.premium_pnl_jpy.jpy,
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
            'trading_pnl_jpy': record.trading_pnl_jpy.jpy,
            'premium_pnl_jpy': record.premium_pnl_jpy.jpy,
            'total_fees_jpy': record.total_fees_jpy.jpy,
        } for record in option_summary_records]

    def _get_option_summary_records(self, data: Dict[str, Any]) -> List:
        from ..processors.option.processor import OptionProcessor
        option_processor = data.get('option_processor')
        
        if option_processor and isinstance(option_processor, OptionProcessor):
            return option_processor.get_summary_records()
        return data.get('option_summary_records', [])

class FinalSummaryReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        summary_records = []
        
        dividend_summary = self._generate_dividend_summary(data.get('dividend_records', []))
        summary_records.append(dividend_summary)
        
        interest_summary = self._generate_interest_summary(data.get('interest_records', []))
        summary_records.append(interest_summary)
        
        stock_summary = self._generate_stock_summary(data.get('stock_records', []))
        summary_records.append(stock_summary)
        
        option_summaries = self._generate_option_summaries(data.get('option_records', []))
        summary_records.extend(option_summaries)
        
        return summary_records

    def _generate_dividend_summary(self, records: List) -> Dict[str, Any]:
        gross_usd = sum(r.gross_amount.usd for r in records)
        tax_usd = sum(r.tax_amount.usd for r in records)
        gross_jpy = sum(r.gross_amount_jpy.jpy for r in records)
        tax_jpy = sum(r.tax_amount_jpy.jpy for r in records)
        
        weighted_rate = self._calculate_weighted_exchange_rate(
            [(r.gross_amount.usd, r.exchange_rate) for r in records]
        )
        
        return {
            'category': '配当収入',
            'subcategory': '受取配当金',
            'gross_amount_usd': gross_usd,
            'tax_amount_usd': tax_usd,
            'net_amount_usd': gross_usd - tax_usd,
            'gross_amount_jpy': gross_jpy,
            'tax_amount_jpy': tax_jpy,
            'net_amount_jpy': gross_jpy - tax_jpy,
        }

    def _generate_interest_summary(self, records: List) -> Dict[str, Any]:
        gross_usd = sum(r.gross_amount.usd for r in records)
        tax_usd = sum(r.tax_amount.usd for r in records)
        gross_jpy = sum(r.gross_amount_jpy.jpy for r in records)
        tax_jpy = sum(r.tax_amount_jpy.jpy for r in records)
        
        weighted_rate = self._calculate_weighted_exchange_rate(
            [(r.gross_amount.usd, r.exchange_rate) for r in records]
        )
        
        return {
            'category': '利子収入',
            'subcategory': '受取利子',
            'gross_amount_usd': gross_usd,
            'tax_amount_usd': tax_usd,
            'net_amount_usd': gross_usd - tax_usd,
            'gross_amount_jpy': gross_jpy,
            'tax_amount_jpy': tax_jpy,
            'net_amount_jpy': gross_jpy - tax_jpy,
        }

    def _generate_stock_summary(self, records: List) -> Dict[str, Any]:
        total_gain_usd = sum(r.realized_gain.usd for r in records)
        total_gain_jpy = sum(r.realized_gain_jpy.jpy for r in records)
        
        weighted_rate = self._calculate_weighted_exchange_rate(
            [(abs(r.realized_gain.usd), r.exchange_rate) for r in records]
        )
        
        return {
            'category': '株式取引',
            'subcategory': '売買損益',
            'gross_amount_usd': total_gain_usd,
            'tax_amount_usd': Decimal('0'),
            'net_amount_usd': total_gain_usd,
            'gross_amount_jpy': total_gain_jpy,
            'tax_amount_jpy': Decimal('0'),
            'net_amount_jpy': total_gain_jpy,
        }

    def _generate_option_summaries(self, records: List) -> List[Dict[str, Any]]:
        summaries = []
        
        trading_gain_usd = sum(r.trading_pnl.usd for r in records)
        trading_gain_jpy = sum(r.trading_pnl_jpy.jpy for r in records)
        
        summaries.append({
            'category': 'オプション取引',
            'subcategory': '取引損益',
            'gross_amount_usd': trading_gain_usd,
            'tax_amount_usd': Decimal('0'),
            'net_amount_usd': trading_gain_usd,
            'gross_amount_jpy': trading_gain_jpy,
            'tax_amount_jpy': Decimal('0'),
            'net_amount_jpy': trading_gain_jpy,
        })
        
        premium_usd = sum(r.premium_pnl.usd for r in records)
        premium_jpy = sum(r.premium_pnl_jpy.jpy for r in records)
        fees_usd = sum(r.fees.usd for r in records)
        fees_jpy = sum(r.fees_jpy.jpy for r in records)
        premium_rate = self._calculate_weighted_exchange_rate(
            [(abs(r.premium_pnl.usd), r.exchange_rate) for r in records]
        )
        
        summaries.append({
            'category': 'オプション取引',
            'subcategory': 'プレミアム収入',
            'gross_amount_usd': premium_usd,
            'tax_amount_usd': fees_usd,
            'net_amount_usd': premium_usd - fees_usd,
            'gross_amount_jpy': premium_jpy,
            'tax_amount_jpy': fees_jpy,
            'net_amount_jpy': premium_jpy - fees_jpy,
        })
        
        return summaries

    def _calculate_weighted_exchange_rate(self, amount_rate_pairs: List[Tuple[Decimal, Decimal]]) -> Decimal:
        total_amount = sum(abs(amount) for amount, _ in amount_rate_pairs)
        if total_amount == 0:
            return Decimal('150.0')
            
        weighted_rate = sum(
            abs(amount) * rate / total_amount 
            for amount, rate in amount_rate_pairs
            if amount != 0
        )
        
        return weighted_rate.quantize(Decimal('0.01'))