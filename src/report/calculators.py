from typing import Dict, List
from ..exchange.money import Money

class ReportCalculator:
    @staticmethod
    def calculate_income_summary(dividend_records: list, interest_records: list) -> Dict[str, Money]:
        """収入サマリーの計算"""
        dividend_total = sum(r.gross_amount for r in dividend_records)
        interest_total = sum(r.gross_amount for r in interest_records)
        tax_total = sum(r.tax_amount for r in dividend_records + interest_records)
        
        return {
            'dividend_total': dividend_total,
            'interest_total': interest_total,
            'tax_total': tax_total,
            'net_total': dividend_total + interest_total - tax_total
        }

    @staticmethod
    def calculate_income_summary_details(records: List) -> Money:
        """収入詳細の計算"""
        return Money(sum(r.gross_amount.usd - r.tax_amount.usd for r in records))

    @staticmethod
    def calculate_stock_summary_details(records: List) -> Money:
        """株式取引サマリーの計算"""
        total_gain = sum(r.realized_gain.usd for r in records)
        return Money(total_gain)

    @staticmethod
    def calculate_option_summary_details(records: List) -> Dict[str, Money]:
        """オプション取引サマリーの計算"""
        return {
            'trading_pnl': Money(sum(r.trading_pnl.usd for r in records)),
            'premium_pnl': Money(sum(r.premium_pnl.usd for r in records)),
            'fees': Money(sum(r.fees.usd for r in records))
        }