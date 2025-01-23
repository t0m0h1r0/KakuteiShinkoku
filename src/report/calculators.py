from typing import Dict, List
from decimal import Decimal
from ..exchange.currency import Currency
from ..exchange.money import Money

class ReportCalculator:
    @staticmethod
    def calculate_income_summary(dividend_records: list, interest_records: list) -> Dict[str, Money]:
        """収入サマリーの計算"""
        # 配当と利子の合計額を計算
        dividend_total = sum((r.gross_amount for r in dividend_records), Money(Decimal('0')))
        interest_total = sum((r.gross_amount for r in interest_records), Money(Decimal('0')))
        tax_total = sum(
            (r.tax_amount for r in dividend_records + interest_records), 
            Money(Decimal('0'))
        )
        
        return {
            'dividend_total': dividend_total,
            'interest_total': interest_total,
            'tax_total': tax_total,
            'net_total': dividend_total + interest_total - tax_total
        }

    @staticmethod
    def calculate_income_summary_details(records: List) -> Dict[str, Money]:
        """収入詳細の計算"""
        total_usd = sum(
            (r.gross_amount - r.tax_amount for r in records), 
            Money(Decimal('0'))
        )
        total_jpy = sum(
            (r.gross_amount_jpy - r.tax_amount_jpy for r in records), 
            Money(Decimal('0'), Currency.JPY)
        )

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
        }

    @staticmethod
    def calculate_stock_summary_details(records: List) -> Dict[str, Money]:
        """株式取引サマリーの計算"""
        total_usd = sum(
            (r.realized_gain for r in records), 
            Money(Decimal('0'))
        )
        total_jpy = sum(
            (r.realized_gain_jpy for r in records), 
            Money(Decimal('0'), Currency.JPY)
        )

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
        }

    @staticmethod
    def calculate_option_summary_details(records: List) -> Dict[str, Money]:
        """オプション取引サマリーの計算"""
        # 取引損益の合計
        trading_pnl = sum(
            (r.trading_pnl for r in records), 
            Money(Decimal('0'))
        )
        trading_pnl_jpy = sum(
            (r.trading_pnl_jpy for r in records), 
            Money(Decimal('0'), Currency.JPY)
        )

        # プレミアム損益の合計
        premium_pnl = sum(
            (r.premium_pnl for r in records), 
            Money(Decimal('0'))
        )
        premium_pnl_jpy = sum(
            (r.premium_pnl_jpy for r in records), 
            Money(Decimal('0'), Currency.JPY)
        )

        # 手数料の合計
        fees = sum(
            (r.fees for r in records), 
            Money(Decimal('0'))
        )
        fees_jpy = sum(
            (r.fees_jpy for r in records), 
            Money(Decimal('0'), Currency.JPY)
        )

        return {
            'total_trading_pnl_usd': trading_pnl,
            'total_trading_pnl_jpy': trading_pnl_jpy,
            'total_premium_pnl_usd': premium_pnl,
            'total_premium_pnl_jpy': premium_pnl_jpy,
            'total_fees_usd': fees,
            'total_fees_jpy': fees_jpy,
        }