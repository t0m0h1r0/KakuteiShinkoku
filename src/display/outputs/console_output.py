from typing import Any, Optional
from .base import BaseOutput
from ..formatters.base import BaseFormatter
from decimal import Decimal
from collections import defaultdict

class ConsoleOutput(BaseOutput):
    """コンソール出力クラス"""

    def output(self, data: Any) -> None:
        """データをコンソールに出力"""
        try:
            formatted_data = self._format_data(data)
            print(formatted_data)
        except Exception as e:
            self.logger.error(f"Error outputting to console: {e}")
            print(str(data))

class ColorConsoleOutput(ConsoleOutput):
    """カラー対応コンソール出力クラス"""
    
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'GREEN': '\033[92m',
        'WARNING': '\033[93m',
        'RED': '\033[91m',
        'END': '\033[0m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m'
    }

    def output(self, data: Any) -> None:
        """データをカラーコンソールに出力"""
        try:
            # リスト型の場合は直接処理
            if isinstance(data, list):
                self._output_list(data)
            else:
                formatted_data = self._format_data(data)
                colored_data = self._apply_colors(formatted_data)
                print(colored_data)
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            print(f"{self.COLORS['BOLD']}Data Summary:{self.COLORS['END']}")
            print(str(data))

    def _output_list(self, records: list) -> None:
        """レコードリストを出力"""
        # レコードを口座ごとにグループ化
        accounts = defaultdict(list)
        for record in records:
            if hasattr(record, 'account_id'):
                accounts[record.account_id].append(record)

        # アカウント別に表示
        for account_id, account_records in accounts.items():
            print(f"\n{self.COLORS['BOLD']}Account: {account_id}{self.COLORS['END']}")
            self._output_account_summary(account_records)

        # 合計サマリーを表示
        if accounts:
            print(f"\n{self.COLORS['HEADER']}Total Summary:{self.COLORS['END']}")
            self._output_total_summary(records)

    def _output_account_summary(self, records: list) -> None:
        """アカウントサマリーを出力"""
        summary = self._calculate_summary(records)
        self._print_summary(summary)

    def _output_total_summary(self, records: list) -> None:
        """合計サマリーを出力"""
        summary = self._calculate_summary(records)
        self._print_summary(summary, is_total=True)

    def _calculate_summary(self, records: list) -> dict:
        """サマリーを計算"""
        summary = {
            'dividend': Decimal('0'),
            'interest': Decimal('0'),
            'cd_interest': Decimal('0'),
            'tax': Decimal('0'),
            'count': len(records)
        }

        for record in records:
            if hasattr(record, 'income_type'):
                amount = record.gross_amount.amount
                if record.income_type == 'Dividend':
                    summary['dividend'] += amount
                elif record.income_type == 'CD Interest':
                    summary['cd_interest'] += amount
                else:
                    summary['interest'] += amount
                summary['tax'] += record.tax_amount.amount

        return summary

    def _print_summary(self, summary: dict, is_total: bool = False) -> None:
        """サマリーを出力"""
        style = self.COLORS['BOLD'] if is_total else ''
        end_style = self.COLORS['END'] if is_total else ''

        if summary['dividend'] > 0:
            print(f"{style}Dividend Total: ${summary['dividend']:.2f}{end_style}")
        if summary['interest'] > 0:
            print(f"{style}Interest Total: ${summary['interest']:.2f}{end_style}")
        if summary['cd_interest'] > 0:
            print(f"{style}CD Interest Total: ${summary['cd_interest']:.2f}{end_style}")
        if summary['tax'] > 0:
            print(f"{self.COLORS['WARNING']}Withholding Tax Total: ${summary['tax']:.2f}{self.COLORS['END']}")
        
        net_total = summary['dividend'] + summary['interest'] + summary['cd_interest'] - summary['tax']
        print(f"{self.COLORS['BOLD']}Net Total: ${net_total:.2f}{self.COLORS['END']}")

    def _apply_colors(self, text: str) -> str:
        """テキストに色を適用"""
        lines = []
        for line in text.split('\n'):
            if 'Account:' in line:
                line = f"{self.COLORS['BOLD']}{line}{self.COLORS['END']}"
            elif 'Total Summary:' in line:
                line = f"\n{self.COLORS['HEADER']}{line}{self.COLORS['END']}"
            elif 'Interest Total:' in line or 'Dividend Total:' in line:
                line = f"{self.COLORS['GREEN']}{line}{self.COLORS['END']}"
            elif 'Tax Total:' in line:
                line = f"{self.COLORS['WARNING']}{line}{self.COLORS['END']}"
            elif 'Net Total:' in line:
                line = f"{self.COLORS['BOLD']}{line}{self.COLORS['END']}"
            lines.append(line)
        return '\n'.join(lines)