from typing import Dict, Any, List, Union
from decimal import Decimal
from collections import defaultdict

from ..formatters.base import BaseFormatter
from ...core.types.money import Money
from ...core.constants.currency import Currency

class TextFormatter(BaseFormatter):
    """テキスト形式のフォーマッタ"""
    
    def format(self, data: Any) -> str:
        """データをテキスト形式でフォーマット"""
        try:
            if isinstance(data, list):
                return self._format_record_list(data)
            elif isinstance(data, dict):
                if self._is_summary_data(data):
                    return self._format_summary_data(data)
            return str(data)
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            return str(data)

    def _format_record_list(self, records: List) -> str:
        """記録リストのフォーマット"""
        if not records:
            return "No records found"
            
        if hasattr(records[0], 'income_type'):
            return self._format_dividend_records(records)
        elif hasattr(records[0], 'trade_type'):
            return self._format_trade_records(records)
        
        return self._format_generic_records(records)

    def _format_dividend_records(self, records: List) -> str:
        """配当記録のフォーマット"""
        accounts = defaultdict(lambda: {
            'Dividend': Decimal('0'),
            'Interest': Decimal('0'),
            'CD Interest': Decimal('0'),
            'Tax': Decimal('0')
        })
        
        for record in records:
            summary = accounts[record.account_id]
            if record.income_type == 'Dividend':
                summary['Dividend'] += record.gross_amount.amount
            elif record.income_type == 'CD Interest':
                summary['CD Interest'] += record.gross_amount.amount
            else:
                summary['Interest'] += record.gross_amount.amount
            summary['Tax'] += record.tax_amount.amount

        lines = []
        for account_id, summary in accounts.items():
            lines.append(f"\nAccount: {account_id}")
            lines.append(f"Dividend Total: ${summary['Dividend']:.2f}")
            lines.append(f"Interest Total: ${summary['Interest']:.2f}")
            if summary['CD Interest'] > 0:
                lines.append(f"CD Interest Total: ${summary['CD Interest']:.2f}")
            lines.append(f"Tax Total: ${summary['Tax']:.2f}")
            net_total = (
                summary['Dividend'] +
                summary['Interest'] +
                summary['CD Interest'] -
                summary['Tax']
            )
            lines.append(f"Net Total: ${net_total:.2f}")

        if len(accounts) > 1:
            # アカウントが複数ある場合は合計を表示
            total = defaultdict(Decimal)
            for summary in accounts.values():
                for key, value in summary.items():
                    total[key] += value
            
            lines.append("\nTotal Summary:")
            lines.append(f"Dividend Total: ${total['Dividend']:.2f}")
            lines.append(f"Interest Total: ${total['Interest']:.2f}")
            if total['CD Interest'] > 0:
                lines.append(f"CD Interest Total: ${total['CD Interest']:.2f}")
            lines.append(f"Tax Total: ${total['Tax']:.2f}")
            net_grand_total = (
                total['Dividend'] +
                total['Interest'] +
                total['CD Interest'] -
                total['Tax']
            )
            lines.append(f"Net Total: ${net_grand_total:.2f}")
        
        return "\n".join(lines)

    def _format_trade_records(self, records: List) -> str:
        """取引記録のフォーマット"""
        stock_records = [r for r in records if not hasattr(r, 'option_type')]
        option_records = [r for r in records if hasattr(r, 'option_type')]

        lines = []
        if stock_records:
            lines.extend(self._format_stock_summary(stock_records))
        if option_records:
            lines.extend(self._format_option_summary(option_records))
        
        return "\n".join(lines)

    def _format_stock_summary(self, records: List) -> List[str]:
        """株式取引サマリーのフォーマット"""
        lines = ["\nStock Trading Summary"]
        lines.append("-" * 30)
        
        total_gain = sum(r.realized_gain.amount for r in records)
        total_volume = sum(r.quantity for r in records if r.action == 'SELL')
        
        lines.append(f"Total Trades: {len(records)}")
        lines.append(f"Total Volume: {total_volume}")
        lines.append(f"Total Realized Gain: ${total_gain:.2f}")
        
        return lines

    def _format_option_summary(self, records: List) -> List[str]:
        """オプション取引サマリーのフォーマット"""
        lines = ["\nOption Trading Summary"]
        lines.append("-" * 30)
        
        total_premium = sum(r.premium_amount.amount for r in records if hasattr(r, 'premium_amount'))
        expired_count = sum(1 for r in records if getattr(r, 'is_expired', False))
        
        lines.append(f"Total Trades: {len(records)}")
        lines.append(f"Total Premium Income: ${total_premium:.2f}")
        lines.append(f"Expired Contracts: {expired_count}")
        
        return lines

    def _is_summary_data(self, data: Dict) -> bool:
        """サマリーデータかどうかを判定"""
        return ('income' in data and 'trading' in data and 'total' in data) or \
               ('accounts' in data and 'total' in data)

    def _format_summary_data(self, data: Dict) -> str:
        """サマリーデータのフォーマット"""
        if 'income' in data:
            return self._format_full_summary(data)
        return self._format_account_summary(data)

    def _format_full_summary(self, data: Dict) -> str:
        """総合サマリーのフォーマット"""
        income = data['income']
        trading = data['trading']
        total = data['total']
        
        lines = ["Investment Summary Report"]
        lines.append("-" * 30)
        
        # 収入サマリー
        lines.append("\nIncome Summary:")
        lines.append(f"Dividend Total: ${income['dividend_total']:.2f}")
        lines.append(f"Interest Total: ${income['interest_total']:.2f}")
        if income['cd_interest_total']:
            lines.append(f"CD Interest Total: ${income['cd_interest_total']:.2f}")
        lines.append(f"Tax Total: ${income['tax_total']:.2f}")
        lines.append(f"Net Income: ${income['net_total']:.2f}")
        
        # 取引サマリー
        lines.append("\nTrading Summary:")
        lines.append(f"Stock Trading Gain: ${trading['stock_gain']:.2f}")
        lines.append(f"Option Trading Gain: ${trading['option_gain']:.2f}")
        lines.append(f"Option Premium Income: ${trading['premium_income']:.2f}")
        lines.append(f"Net Trading Gain: ${trading['net_total']:.2f}")
        
        # 総合計
        lines.append("\nTotal Summary:")
        lines.append(f"Total Income: ${total['total_income']:.2f}")
        lines.append(f"Total Trading: ${total['total_trading']:.2f}")
        lines.append(f"Grand Total: ${total['grand_total']:.2f}")
        
        return "\n".join(lines)

    def _format_account_summary(self, data: Dict) -> str:
        """アカウント別サマリーのフォーマット"""
        lines = []
        
        for account_id, summary in data['accounts'].items():
            lines.append(f"\nAccount: {account_id}")
            lines.append(f"Dividend Total: ${summary['Dividend']:.2f}")
            lines.append(f"Interest Total: ${summary['Interest']:.2f}")
            if summary['CD Interest']:
                lines.append(f"CD Interest Total: ${summary['CD Interest']:.2f}")
            lines.append(f"Tax Total: ${summary['Tax']:.2f}")
            
            net_total = (
                summary['Dividend'] +
                summary['Interest'] +
                summary['CD Interest'] -
                summary['Tax']
            )
            lines.append(f"Net Total: ${net_total:.2f}")
        
        if data['total']:
            lines.append("\nTrading Summary")
            lines.append("-" * 30)
            lines.append(f"Stock Trading Gain: ${data['total']['stock_gain']:.2f}")
            lines.append(f"Option Trading Gain: ${data['total']['option_gain']:.2f}")
            lines.append(f"Option Premium Income: ${data['total']['premium']:.2f}")
        
        return "\n".join(lines)
        
    def _format_generic_records(self, records: List) -> str:
        """一般的な記録のフォーマット"""
        return "\n".join(str(record) for record in records)