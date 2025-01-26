from typing import Dict, List
from ..exchange.money import Money
from ..exchange.currency import Currency

class ReportCalculator:
    @staticmethod
    def calculate_income_summary(dividend_records: list, interest_records: list) -> Dict[str, Money]:
        """収入サマリーの計算"""
        if not dividend_records and not interest_records:
            zero_money = Money(0, Currency.USD)
            return {
                'dividend_total': zero_money,
                'interest_total': zero_money,
                'tax_total': zero_money,
                'net_total': zero_money
            }

        dividend_total = sum((r.gross_amount for r in dividend_records), Money(0, Currency.USD))
        interest_total = sum((r.gross_amount for r in interest_records), Money(0, Currency.USD))
        tax_total = sum((r.tax_amount for r in dividend_records + interest_records), Money(0, Currency.USD))
        
        return {
            'dividend_total': dividend_total,
            'interest_total': interest_total,
            'tax_total': tax_total,
            'net_total': dividend_total + interest_total - tax_total
        }

    @staticmethod
    def calculate_stock_summary_details(records: List) -> Money:
        """株式取引サマリーの計算"""
        return sum((r.realized_gain for r in records), Money(0, Currency.USD))

    @staticmethod
    def calculate_option_summary_details(records: List) -> Dict[str, Money]:
        """オプション取引サマリーの計算"""
        return {
            'trading_pnl': sum((r.trading_pnl for r in records), Money(0, Currency.USD)),
            'premium_pnl': sum((r.premium_pnl for r in records), Money(0, Currency.USD)),
            'fees': sum((r.fees for r in records), Money(0, Currency.USD))
        }
