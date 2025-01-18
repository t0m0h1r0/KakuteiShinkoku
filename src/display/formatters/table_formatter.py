from typing import Dict, Any, List
from decimal import Decimal
from .base import BaseFormatter
from ...core.types.money import Money

class TableFormatter(BaseFormatter):
    """表形式のフォーマッタ"""
    
    def __init__(self):
        self.headers = ['Category', 'USD Amount', 'JPY Amount']
        self.widths = [20, 15, 20]
        self.separator = '+' + '+'.join('-' * width for width in self.widths) + '+'

    def format(self, data: Dict[str, Dict[str, Any]]) -> str:
        """アカウントサマリーを表形式でフォーマット"""
        output = []
        
        # アカウント別サマリー
        for account, summary in data.get('accounts', {}).items():
            output.append(f"\nAccount: {account}")
            output.extend(self._format_table(summary))
            output.append("")  # 空行
        
        # 合計サマリー
        output.append("Total Summary:")
        total_summary = data.get('total', {})
        output.extend(self._format_table(total_summary))
        
        return "\n".join(output)

    def _format_table(self, summary: Dict[str, Any]) -> List[str]:
        """単一テーブルのフォーマット"""
        lines = []
        
        # ヘッダー
        lines.append(self.separator)
        lines.append(
            '|{:^20}|{:^15}|{:^20}|'.format(*self.headers)
        )
        lines.append(self.separator)
        
        # データ行
        row_format = '|{:<20}|{:>15}|{:>20}|'
        
        # CD Principal
        if summary.get('principal', Money(Decimal('0'))).amount > 0:
            lines.append(
                self._format_row(row_format, 'CD Principal',
                               summary['principal'], None)
            )
        
        # CD Interest
        if summary.get('CD Interest', Money(Decimal('0'))).amount > 0:
            lines.append(
                self._format_row(row_format, 'CD Interest',
                               summary['CD Interest'],
                               summary.get('cd_interest_jpy', Money(Decimal('0'))))
            )
        
        # Dividend
        lines.append(
            self._format_row(row_format, 'Dividends',
                           summary['Dividend'],
                           summary.get('dividend_jpy', Money(Decimal('0'))))
        )
        
        # Other Interest
        lines.append(
            self._format_row(row_format, 'Other Interest',
                           summary['Interest'],
                           summary.get('interest_jpy', Money(Decimal('0'))))
        )
        
        # Tax
        lines.append(
            self._format_row(row_format, 'Withholding Tax',
                           summary['Tax'],
                           summary.get('tax_jpy', Money(Decimal('0'))))
        )
        
        lines.append(self.separator)
        
        # Net Income
        net_income = self._calculate_net_income(summary)
        lines.append(
            self._format_row(row_format, 'Net Income',
                           net_income['usd'],
                           net_income['jpy'])
        )
        
        lines.append(self.separator)
        return lines

    def _format_row(self, format_str: str, label: str,
                   usd_amount: Money, jpy_amount: Money = None) -> str:
        """表の1行をフォーマット"""
        usd_str = self._format_currency(usd_amount)
        jpy_str = (f"¥{self._format_money(jpy_amount, 0)}"
                  if jpy_amount else '')
        return format_str.format(label, usd_str, jpy_str)

    def _calculate_net_income(self, summary: Dict[str, Any]) -> Dict[str, Money]:
        """純収入を計算"""
        total_income_usd = Money(
            summary['Dividend'].amount +
            summary['Interest'].amount +
            summary.get('CD Interest', Money(Decimal('0'))).amount
        )
        
        total_income_jpy = Money(
            summary.get('dividend_jpy', Money(Decimal('0'))).amount +
            summary.get('interest_jpy', Money(Decimal('0'))).amount +
            summary.get('cd_interest_jpy', Money(Decimal('0'))).amount
        )
        
        return {
            'usd': Money(total_income_usd.amount - summary['Tax'].amount),
            'jpy': Money(total_income_jpy.amount - summary.get('tax_jpy', Money(Decimal('0'))).amount)
        }