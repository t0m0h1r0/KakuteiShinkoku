from typing import Any, Optional, List
from decimal import Decimal
from collections import defaultdict

from .base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter

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
            elif isinstance(data, dict):
                formatted_data = self._format_data(data)
                colored_data = self._apply_colors(formatted_data)
                print(colored_data)
            else:
                print(str(data))
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            print(f"{self.COLORS['BOLD']}Data Summary:{self.COLORS['END']}")
            print(str(data))

    def _output_list(self, records: List) -> None:
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

    def _output_dividend_summary(self, records: List) -> None:
        """配当サマリーを出力"""
        accounts = self._calculate_dividend_summary(records)
        
        print(f"\n{self.COLORS['HEADER']}Dividend Income Summary:{self.COLORS['END']}")
        
        # アカウント別の出力
        for account_id, summary in accounts.items():
            if account_id != 'total':  # 合計以外を出力
                print(f"\n{self.COLORS['BOLD']}Account: {account_id}{self.COLORS['END']}")
                print(f"Total Amount: ${summary['amount']:.2f}")

        # 全体の合計を出力（複数アカウントの場合のみ）
        if len(accounts) > 2:  # 'total'を含むので2より大きい場合
            print(f"\n{self.COLORS['BOLD']}Total Dividend Summary:{self.COLORS['END']}")
            total_amount = accounts['total']['amount']
            print(f"Total Dividend: ${total_amount:.2f}")

    def _output_interest_summary(self, records: List) -> None:
        """利子サマリーを出力"""
        accounts = self._calculate_interest_summary(records)
        
        print(f"\n{self.COLORS['HEADER']}Interest Income Summary:{self.COLORS['END']}")
        
        # アカウント別の出力
        for account_id, summary in accounts.items():
            if account_id != 'total':  # 合計以外を出力
                print(f"\n{self.COLORS['BOLD']}Account: {account_id}{self.COLORS['END']}")
                print(f"Total Amount: ${summary['amount']:.2f}")

        # 全体の合計を出力（複数アカウントの場合のみ）
        if len(accounts) > 2:  # 'total'を含むので2より大きい場合
            print(f"\n{self.COLORS['BOLD']}Total Interest Summary:{self.COLORS['END']}")
            total_amount = accounts['total']['amount']
            print(f"Total Interest: ${total_amount:.2f}")

    def _output_investment_summary(self, summary: dict) -> None:
        """投資サマリーをカラー出力"""
        print(f"\n{self.COLORS['HEADER']}Investment Summary Report{self.COLORS['END']}")
        
        if 'income' in summary:
            print(f"\n{self.COLORS['BLUE']}Income Summary:{self.COLORS['END']}")
            income = summary['income']
            print(f"Dividend Total: ${income['dividend_total']:.2f}")
            print(f"Interest Total: ${income['interest_total']:.2f}")
            print(f"Tax Total: ${income['tax_total']:.2f}")
            print(f"Net Income: ${income['net_total']:.2f}")
        
        if 'trading' in summary:
            print(f"\n{self.COLORS['GREEN']}Trading Summary:{self.COLORS['END']}")
            trading = summary['trading']
            print(f"Stock Trading Gain: ${trading['stock_gain']:.2f}")
            print(f"Option Trading Gain: ${trading['option_gain']:.2f}")
            print(f"Option Premium Income: ${trading['premium_income']:.2f}")
            print(f"Net Trading Gain: ${trading['net_total']:.2f}")
        
        if 'total' in summary:
            print(f"\n{self.COLORS['BOLD']}Total Summary:{self.COLORS['END']}")
            total = summary['total']
            print(f"Total Income: ${total['total_income']:.2f}")
            print(f"Total Trading: ${total['total_trading']:.2f}")
            print(f"Grand Total: ${total['grand_total']:.2f}")

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'

    def _calculate_dividend_summary(self, records: list) -> dict:
        """配当サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
        
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts

    def _calculate_interest_summary(self, records: list) -> dict:
        """利子サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
        
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts

    def _apply_colors(self, text: str) -> str:
        """テキストに色を適用"""
        lines = []
        for line in text.split('\n'):
            if 'Summary:' in line:
                line = f"\n{self.COLORS['HEADER']}{line}{self.COLORS['END']}"
            elif 'Total:' in line:
                line = f"{self.COLORS['GREEN']}{line}{self.COLORS['END']}"
            lines.append(line)
        return '\n'.join(lines)

class ImprovedConsoleOutput(BaseOutput):
    """改善されたコンソール出力クラス"""

    def output(self, data: Any) -> None:
        """データをコンソールに出力"""
        try:
            if isinstance(data, list):
                self._output_summary(data)
            elif isinstance(data, dict):
                self._output_investment_summary(data)
            else:
                print(str(data))
        except Exception as e:
            self.logger.error(f"出力エラー: {e}")
            print(str(data))

    def _output_summary(self, records: list) -> None:
        """レコードの要約を出力"""
        dividend_records = [r for r in records if self._is_dividend_record(r)]
        interest_records = [r for r in records if self._is_interest_record(r)]
        
        print("\n【投資収入サマリー】")
        self._print_income_summary(dividend_records, interest_records)

    def _output_investment_summary(self, summary: dict) -> None:
        """投資サマリーを出力"""
        print("\n【投資総合レポート】")
        
        if 'income' in summary:
            print("\n収入詳細:")
            income = summary['income']
            print(f"配当総額: ${income['dividend_total']:.2f}")
            print(f"利子総額: ${income['interest_total']:.2f}")
            print(f"税金総額: ${income['tax_total']:.2f}")
            print(f"純収入: ${income['net_total']:.2f}")
        
        if 'trading' in summary:
            print("\n取引損益:")
            trading = summary['trading']
            print(f"株式取引損益: ${trading['stock_gain']:.2f}")
            print(f"オプション取引損益: ${trading['option_gain']:.2f}")
            print(f"オプションプレミアム収入: ${trading['premium_income']:.2f}")
            print(f"純取引損益: ${trading['net_total']:.2f}")
        
        if 'total' in summary:
            print("\n総合計:")
            total = summary['total']
            print(f"総収入: ${total['total_income']:.2f}")
            print(f"総取引損益: ${total['total_trading']:.2f}")
            print(f"総合計: ${total['grand_total']:.2f}")

    def _print_income_summary(self, dividend_records, interest_records):
        """収入の詳細を出力"""
        div_accounts = self._calculate_dividend_summary(dividend_records)
        int_accounts = self._calculate_interest_summary(interest_records)
        
        print("\n配当サマリー:")
        for account, summary in div_accounts.items():
            if account != 'total':
                print(f"アカウント {account}: ${summary['amount']:.2f}")
        
        print("\n利子サマリー:")
        for account, summary in int_accounts.items():
            if account != 'total':
                print(f"アカウント {account}: ${summary['amount']:.2f}")
        
        # 複数アカウントがある場合のみ総計を表示
        if len(div_accounts) > 2 or len(int_accounts) > 2:
            print("\n総合計:")
            div_total = div_accounts.get('total', {'amount': 0})['amount']
            int_total = int_accounts.get('total', {'amount': 0})['amount']
            print(f"配当総額: ${div_total:.2f}")
            print(f"利子総額: ${int_total:.2f}")
            print(f"総収入: ${div_total + int_total:.2f}")

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'

    def _calculate_dividend_summary(self, records: list) -> dict:
        """配当サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
        
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts

    def _calculate_interest_summary(self, records: list) -> dict:
        """利子サマリーを計算"""
        accounts = defaultdict(lambda: {'amount': Decimal('0'), 'count': 0})
        
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['count'] += 1
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'count': 0}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['count'] += account['count']
        
        accounts['total'] = total
        return accounts