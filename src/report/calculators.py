from typing import Dict, List
from decimal import Decimal

class ReportCalculator:
    """レポート計算のユーティリティクラス"""
    
    @staticmethod
    def calculate_income_summary(
        dividend_records: list, 
        interest_records: list
    ) -> Dict[str, Decimal]:
        """
        収入サマリーを計算
        
        Args:
            dividend_records (list): 配当レコード
            interest_records (list): 利子レコード
        
        Returns:
            Dict[str, Decimal]: 収入サマリー
        """
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

    @staticmethod
    def calculate_trading_summary(
        stock_records: list, 
        option_records: list
    ) -> Dict[str, Decimal]:
        """
        取引損益サマリーを計算
        
        Args:
            stock_records (list): 株式取引レコード
            option_records (list): オプション取引レコード
        
        Returns:
            Dict[str, Decimal]: 取引損益サマリー
        """
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

    @staticmethod
    def calculate_income_summary_details(records: List) -> Dict[str, Decimal]:
        """
        収入の詳細サマリーを計算
        
        Args:
            records (List): 収入レコードのリスト
        
        Returns:
            Dict[str, Decimal]: 収入詳細サマリー
        """
        total_usd = Decimal('0')
        total_jpy = Decimal('0')
        exchange_rate_sum = Decimal('0')
        count = 0

        for record in records:
            total_usd += record.gross_amount.amount - record.tax_amount.amount
            total_jpy += record.gross_amount_jpy.amount - record.tax_amount_jpy.amount
            exchange_rate_sum += record.exchange_rate
            count += 1

        return {
            'total_usd': total_usd,
            'total_jpy': total_jpy,
            'exchange_rate': exchange_rate_sum / count if count > 0 else Decimal('150.0')
        }

    @staticmethod
    def calculate_stock_summary_details(records: List) -> Dict[str, Decimal]:
        """
        株式取引サマリーの詳細を計算
        
        Args:
            records (List): 株式取引レコードのリスト
        
        Returns:
            Dict[str, Decimal]: 株式取引サマリー詳細
        """
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

    @staticmethod
    def calculate_option_summary_details(records: List) -> Dict[str, Decimal]:
        """
        オプション取引サマリーの詳細を計算
        
        Args:
            records (List): オプション取引レコードのリスト
        
        Returns:
            Dict[str, Decimal]: オプション取引サマリー詳細
        """
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
