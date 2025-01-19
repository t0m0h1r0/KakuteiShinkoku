from typing import Any, Optional
from decimal import Decimal
from collections import defaultdict

from .base import BaseOutput
from ..formatters.base import BaseFormatter

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
        # 配当と利子のレコードを分離
        dividend_records = [r for r in records if self._is_dividend_record(r)]
        interest_records = [r for r in records if self._is_interest_record(r)]

        # 配当の出力
        if dividend_records:
            self._output_dividend_summary(dividend_records)

        # 利子の出力
        if interest_records:
            if dividend_records:  # 配当の出力がある場合は空行を追加
                print("")
            self._output_interest_summary(interest_records)

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'

    def _output_dividend_summary(self, records: list) -> None:
        """配当サマリーを出力"""
        accounts = self._calculate_dividend_summary(records)
        
        print(f"\n{self.COLORS['HEADER']}Dividend Income Summary:{self.COLORS['END']}")
        
        # アカウント別の出力
        for account_id, summary in accounts.items():
            if account_id != 'total':  # 合計以外を出力
                print(f"\n{self.COLORS['BOLD']}Account: {account_id}{self.COLORS['END']}")
                self._print_account_summary(summary)
        
        # 全体の合計を出力（複数アカウントの場合のみ）
        if len(accounts) > 2:  # 'total'を含むので2より大きい場合
            print(f"\n{self.COLORS['BOLD']}Total Dividend Summary:{self.COLORS['END']}")
            self._print_account_summary(accounts['total'])

    def _output_interest_summary(self, records: list) -> None:
        """利子サマリーを出力"""
        accounts = self._calculate_interest_summary(records)
        
        print(f"\n{self.COLORS['HEADER']}Interest Income Summary:{self.COLORS['END']}")
        
        # アカウント別の出力
        for account_id, summary in accounts.items():
            if account_id != 'total':  # 合計以外を出力
                print(f"\n{self.COLORS['BOLD']}Account: {account_id}{self.COLORS['END']}")
                self._print_account_summary(summary)
        
        # 全体の合計を出力（複数アカウントの場合のみ）
        if len(accounts) > 2:  # 'total'を含むので2より大きい場合
            print(f"\n{self.COLORS['BOLD']}Total Interest Summary:{self.COLORS['END']}")
            self._print_account_summary(accounts['total'])

    def _calculate_dividend_summary(self, records: list) -> dict:
        """配当サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'tax': Decimal('0'), 'count': 0})
        
        # アカウント別の集計
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['tax'] += record.tax_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'tax': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['tax'] += account['tax']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts

    def _calculate_interest_summary(self, records: list) -> dict:
        """利子サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'tax': Decimal('0'), 'count': 0})
        
        # アカウント別の集計
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['tax'] += record.tax_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'tax': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['tax'] += account['tax']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts

    def _print_account_summary(self, summary: dict) -> None:
        """アカウントサマリーを出力"""
        if summary['amount'] > 0:
            print(f"Total Amount: ${summary['amount']:.2f}")
        if summary['tax'] > 0:
            print(f"{self.COLORS['WARNING']}Tax Total: ${summary['tax']:.2f}{self.COLORS['END']}")
        
        net_total = summary['amount'] - summary['tax']
        print(f"{self.COLORS['BOLD']}Net Total: ${net_total:.2f}{self.COLORS['END']}")

    def _apply_colors(self, text: str) -> str:
        """テキストに色を適用"""
        lines = []
        for line in text.split('\n'):
            if 'Account:' in line:
                line = f"{self.COLORS['BOLD']}{line}{self.COLORS['END']}"
            elif 'Summary:' in line:
                line = f"\n{self.COLORS['HEADER']}{line}{self.COLORS['END']}"
            elif 'Amount:' in line or 'Total:' in line:
                line = f"{self.COLORS['GREEN']}{line}{self.COLORS['END']}"
            elif 'Tax:' in line:
                line = f"{self.COLORS['WARNING']}{line}{self.COLORS['END']}"
            elif 'Net:' in line:
                line = f"{self.COLORS['BOLD']}{line}{self.COLORS['END']}"
            lines.append(line)
        return '\n'.join(lines)