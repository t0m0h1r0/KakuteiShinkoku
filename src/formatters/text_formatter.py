from typing import Dict, Any, List, Union
from decimal import Decimal
from collections import defaultdict

from .base_formatter import BaseFormatter
from ..exchange.money import Money
from ..exchange.money import Currency

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

    def _format_money(self, amount: Decimal, is_jpy: bool = False) -> str:
        """金額のフォーマット処理"""
        if is_jpy:
            return f"¥{int(amount):,}"
        return f"${amount:,.2f}"

    def _format_record_list(self, records: List) -> str:
        """記録リストのフォーマット"""
        if not records:
            return "No records found"

        # 配当と利子のレコードを分離
        dividend_records = [r for r in records if self._is_dividend_record(r)]
        interest_records = [r for r in records if self._is_interest_record(r)]
        
        lines = []
        
        if dividend_records:
            lines.extend(self._format_dividend_records(dividend_records))
        
        if interest_records:
            if lines:
                lines.append("")
            lines.extend(self._format_interest_records(interest_records))
        
        return "\n".join(lines)

    def _format_dividend_records(self, records: List) -> List[str]:
        """配当記録のフォーマット"""
        accounts = defaultdict(lambda: {
            'amount_usd': Decimal('0'),
            'tax_usd': Decimal('0'),
            'amount_jpy': Decimal('0'),
            'tax_jpy': Decimal('0')
        })
        
        for record in records:
            acc = accounts[record.account_id]
            acc['amount_usd'] += record.gross_amount.amount
            acc['tax_usd'] += record.tax_amount.amount
            acc['amount_jpy'] += record.gross_amount_jpy.amount
            acc['tax_jpy'] += record.tax_amount_jpy.amount

        lines = ["配当収入:"]
        for account_id, summary in accounts.items():
            net_usd = summary['amount_usd'] - summary['tax_usd']
            net_jpy = summary['amount_jpy'] - summary['tax_jpy']
            
            lines.append(f"\nアカウント: {account_id}")
            lines.append(f"配当総額: {self._format_money(summary['amount_usd'])} ({self._format_money(summary['amount_jpy'], True)})")
            lines.append(f"税額合計: {self._format_money(summary['tax_usd'])} ({self._format_money(summary['tax_jpy'], True)})")
            lines.append(f"受取配当金: {self._format_money(net_usd)} ({self._format_money(net_jpy, True)})")

        if len(accounts) > 1:
            total_amount_usd = sum(s['amount_usd'] for s in accounts.values())
            total_tax_usd = sum(s['tax_usd'] for s in accounts.values())
            total_amount_jpy = sum(s['amount_jpy'] for s in accounts.values())
            total_tax_jpy = sum(s['tax_jpy'] for s in accounts.values())
            net_total_usd = total_amount_usd - total_tax_usd
            net_total_jpy = total_amount_jpy - total_tax_jpy
            
            lines.append("\n配当総合計:")
            lines.append(f"配当総額: {self._format_money(total_amount_usd)} ({self._format_money(total_amount_jpy, True)})")
            lines.append(f"税額合計: {self._format_money(total_tax_usd)} ({self._format_money(total_tax_jpy, True)})")
            lines.append(f"受取配当金: {self._format_money(net_total_usd)} ({self._format_money(net_total_jpy, True)})")

        return lines

    def _format_interest_records(self, records: List) -> List[str]:
        """利子記録のフォーマット"""
        accounts = defaultdict(lambda: {
            'amount_usd': Decimal('0'),
            'tax_usd': Decimal('0'),
            'amount_jpy': Decimal('0'),
            'tax_jpy': Decimal('0')
        })
        
        for record in records:
            acc = accounts[record.account_id]
            acc['amount_usd'] += record.gross_amount.amount
            acc['tax_usd'] += record.tax_amount.amount
            acc['amount_jpy'] += record.gross_amount_jpy.amount
            acc['tax_jpy'] += record.tax_amount_jpy.amount

        lines = ["利子収入:"]
        for account_id, summary in accounts.items():
            net_usd = summary['amount_usd'] - summary['tax_usd']
            net_jpy = summary['amount_jpy'] - summary['tax_jpy']
            
            lines.append(f"\nアカウント: {account_id}")
            lines.append(f"利子総額: {self._format_money(summary['amount_usd'])} ({self._format_money(summary['amount_jpy'], True)})")
            lines.append(f"税額合計: {self._format_money(summary['tax_usd'])} ({self._format_money(summary['tax_jpy'], True)})")
            lines.append(f"受取利子: {self._format_money(net_usd)} ({self._format_money(net_jpy, True)})")

        if len(accounts) > 1:
            total_amount_usd = sum(s['amount_usd'] for s in accounts.values())
            total_tax_usd = sum(s['tax_usd'] for s in accounts.values())
            total_amount_jpy = sum(s['amount_jpy'] for s in accounts.values())
            total_tax_jpy = sum(s['tax_jpy'] for s in accounts.values())
            net_total_usd = total_amount_usd - total_tax_usd
            net_total_jpy = total_amount_jpy - total_tax_jpy
            
            lines.append("\n利子総合計:")
            lines.append(f"利子総額: {self._format_money(total_amount_usd)} ({self._format_money(total_amount_jpy, True)})")
            lines.append(f"税額合計: {self._format_money(total_tax_usd)} ({self._format_money(total_tax_jpy, True)})")
            lines.append(f"受取利子: {self._format_money(net_total_usd)} ({self._format_money(net_total_jpy, True)})")

        return lines

    def _format_full_summary(self, data: Dict) -> str:
        """総合サマリーのフォーマット"""
        income = data['income']
        trading = data['trading']
        total = data['total']
        
        lines = ["投資サマリーレポート"]
        lines.append("-" * 40)
        
        # 収入サマリー
        lines.append("\n収入サマリー:")
        lines.append(f"配当総額: {self._format_money(income['dividend_total_usd'])} ({self._format_money(income['dividend_total_jpy'], True)})")
        lines.append(f"利子総額: {self._format_money(income['interest_total_usd'])} ({self._format_money(income['interest_total_jpy'], True)})")
        lines.append(f"税金合計: {self._format_money(income['tax_total_usd'])} ({self._format_money(income['tax_total_jpy'], True)})")
        lines.append(f"純収入: {self._format_money(income['net_total_usd'])} ({self._format_money(income['net_total_jpy'], True)})")
        
        # 取引サマリー
        lines.append("\n取引サマリー:")
        lines.append(f"株式取引損益: {self._format_money(trading['stock_gain_usd'])} ({self._format_money(trading['stock_gain_jpy'], True)})")
        lines.append(f"オプション取引損益: {self._format_money(trading['option_gain_usd'])} ({self._format_money(trading['option_gain_jpy'], True)})")
        lines.append(f"オプションプレミアム収入: {self._format_money(trading['premium_income_usd'])} ({self._format_money(trading['premium_income_jpy'], True)})")
        lines.append(f"純取引損益: {self._format_money(trading['net_total_usd'])} ({self._format_money(trading['net_total_jpy'], True)})")
        
        # 総合計
        lines.append("\n総合計:")
        lines.append(f"総収入: {self._format_money(total['total_income_usd'])} ({self._format_money(total['total_income_jpy'], True)})")
        lines.append(f"総取引損益: {self._format_money(total['total_trading_usd'])} ({self._format_money(total['total_trading_jpy'], True)})")
        lines.append(f"最終合計: {self._format_money(total['grand_total_usd'])} ({self._format_money(total['grand_total_jpy'], True)})")
        
        return "\n".join(lines)

    def _format_account_summary(self, data: Dict) -> str:
        """アカウント別サマリーのフォーマット"""
        lines = []
        
        for account_id, summary in data['accounts'].items():
            lines.append(f"\nアカウント: {account_id}")
            
            if 'dividend' in summary and summary['dividend_usd'] > 0:
                lines.append(f"配当総額: {self._format_money(summary['dividend_usd'])} ({self._format_money(summary['dividend_jpy'], True)})")
            
            if 'interest' in summary and summary['interest_usd'] > 0:
                lines.append(f"利子総額: {self._format_money(summary['interest_usd'])} ({self._format_money(summary['interest_jpy'], True)})")
            
            if 'tax' in summary and summary['tax_usd'] > 0:
                lines.append(f"税金合計: {self._format_money(summary['tax_usd'])} ({self._format_money(summary['tax_jpy'], True)})")
            
            net_total_usd = summary.get('dividend_usd', Decimal('0')) + \
                           summary.get('interest_usd', Decimal('0')) - \
                           summary.get('tax_usd', Decimal('0'))
            net_total_jpy = summary.get('dividend_jpy', Decimal('0')) + \
                           summary.get('interest_jpy', Decimal('0')) - \
                           summary.get('tax_jpy', Decimal('0'))
            lines.append(f"純収入: {self._format_money(net_total_usd)} ({self._format_money(net_total_jpy, True)})")
        
        return "\n".join(lines)