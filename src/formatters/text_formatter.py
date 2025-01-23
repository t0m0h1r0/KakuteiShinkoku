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

    def _is_summary_data(self, data: Dict) -> bool:
        """データがサマリータイプかを判定"""
        return all(key in data for key in ['income', 'trading', 'total'])

    def _format_summary_data(self, data: Dict) -> str:
        """総合サマリーのフォーマット"""
        income = data['income']
        trading = data['trading']
        total = data['total']
        
        lines = ["投資サマリーレポート"]
        lines.append("-" * 40)
        
        # 収入サマリー
        lines.append("\n収入サマリー:")
        lines.append(f"配当総額: ${income['dividend_total'].usd:,.2f}")
        lines.append(f"利子総額: ${income['interest_total'].usd:,.2f}")
        lines.append(f"税金合計: ${income['tax_total'].usd:,.2f}")
        lines.append(f"純収入: ${income['net_total'].usd:,.2f}")
        
        # 取引サマリー
        lines.append("\n取引サマリー:")
        lines.append(f"株式取引損益: ${trading['stock_gain'].usd:,.2f}")
        lines.append(f"オプション取引損益: ${trading['option_gain'].usd:,.2f}")
        lines.append(f"オプションプレミアム収入: ${trading['premium_income'].usd:,.2f}")
        lines.append(f"純取引損益: ${trading['net_total'].usd:,.2f}")
        
        # 総合計
        lines.append("\n総合計:")
        lines.append(f"総収入: ${total['total_income'].usd:,.2f}")
        lines.append(f"総取引損益: ${total['total_trading'].usd:,.2f}")
        lines.append(f"最終合計: ${total['grand_total'].usd:,.2f}")
        
        return "\n".join(lines)

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

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'