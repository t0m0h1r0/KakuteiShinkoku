from typing import Dict, List
from decimal import Decimal
from ..exchange.currency import Currency

class ReportCalculator:
    @staticmethod
    def calculate_income_summary(dividend_records: list, interest_records: list) -> Dict[str, Decimal]:
        summary = {
            'dividend_total': sum(r.gross_amount.usd for r in dividend_records),
            'interest_total': sum(r.gross_amount.usd for r in interest_records),
            'tax_total': sum(r.tax_amount.usd 
                           for r in dividend_records + interest_records)
        }
        
        summary['net_total'] = (
            summary['dividend_total'] +
            summary['interest_total'] -
            summary['tax_total']
        )
        
        return summary

    @staticmethod
    def calculate_income_summary_details(records: List) -> Dict[str, Decimal]:
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        count = 0

        for record in records:
            total_usd += record.gross_amount.usd - record.tax_amount.usd
            total_jpy += record.gross_amount.jpy - record.tax_amount.jpy
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
        }

    @staticmethod
    def calculate_stock_summary_details(records: List) -> Dict[str, Decimal]:
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            total_usd += record.realized_gain.usd
            total_jpy += record.realized_gain.jpy
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
        }

    @staticmethod
    def calculate_option_summary_details(records: List) -> Dict[str, Decimal]:
        trading_pnl_usd = Decimal('0')
        trading_pnl_jpy = Decimal('0')
        premium_pnl_usd = Decimal('0')
        premium_pnl_jpy = Decimal('0')
        fees_usd = Decimal('0')
        fees_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            trading_pnl_usd += record.trading_pnl.usd
            trading_pnl_jpy += record.trading_pnl.jpy
            premium_pnl_usd += record.premium_pnl.usd
            premium_pnl_jpy += record.premium_pnl.jpy
            fees_usd += record.fees.usd
            fees_jpy += record.fees.jpy
            count += 1

        return {
            'total_trading_pnl_usd': trading_pnl_usd,
            'total_trading_pnl_jpy': trading_pnl_jpy,
            'total_premium_pnl_usd': premium_pnl_usd,
            'total_premium_pnl_jpy': premium_pnl_jpy,
            'total_fees_usd': fees_usd,
            'total_fees_jpy': fees_jpy,
        }