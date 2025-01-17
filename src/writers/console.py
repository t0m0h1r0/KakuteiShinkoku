from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date

from .base import BaseWriter, Record
from ..core.models import DividendRecord, Money
from ..config.constants import Currency

class ConsoleWriter(BaseWriter):
    """コンソール出力クラス"""

    def write(self, records: List[Record]) -> None:
        """アカウント別サマリーと総合計を出力"""
        try:
            account_summary = self._create_account_summary(records)
            self._print_account_summaries(account_summary)
            self._print_total_summary(account_summary)
        except Exception as e:
            self._logger.error(f"Console output error: {e}")

    def _create_account_summary(self, records: List[DividendRecord]) -> Dict[str, Dict[str, Money]]:
        """アカウント別の集計を作成"""
        summary: Dict[str, Dict[str, Money]] = {}
        
        for record in records:
            if record.account_id not in summary:
                summary[record.account_id] = self._create_empty_summary()
            
            self._update_summary(summary[record.account_id], record)
        
        return summary

    @staticmethod
    def _create_empty_summary() -> Dict[str, Money]:
        """新しい集計辞書を作成"""
        return {
            'dividend': Money(Decimal('0')),
            'interest': Money(Decimal('0')),
            'cd_interest': Money(Decimal('0')),
            'tax': Money(Decimal('0')),
            'dividend_jpy': Money(Decimal('0'), Currency.JPY),
            'interest_jpy': Money(Decimal('0'), Currency.JPY),
            'cd_interest_jpy': Money(Decimal('0'), Currency.JPY),
            'tax_jpy': Money(Decimal('0'), Currency.JPY),
            'principal': Money(Decimal('0'))
        }

    def _update_summary(self, summary: Dict[str, Money], record: DividendRecord) -> None:
        """集計を更新"""
        if record.income_type == 'CD Interest':
            summary['cd_interest'] = Money(
                summary['cd_interest'].amount + record.gross_amount.amount
            )
            summary['cd_interest_jpy'] = Money(
                summary['cd_interest_jpy'].amount + record.gross_amount_jpy.amount,
                Currency.JPY
            )
            summary['principal'] = Money(
                summary['principal'].amount + record.principal_amount.amount
            )
        elif record.income_type == 'Dividend':
            summary['dividend'] = Money(
                summary['dividend'].amount + record.gross_amount.amount
            )
            summary['dividend_jpy'] = Money(
                summary['dividend_jpy'].amount + record.gross_amount_jpy.amount,
                Currency.JPY
            )
        else:
            summary['interest'] = Money(
                summary['interest'].amount + record.gross_amount.amount
            )
            summary['interest_jpy'] = Money(
                summary['interest_jpy'].amount + record.gross_amount_jpy.amount,
                Currency.JPY
            )
        
        summary['tax'] = Money(
            summary['tax'].amount + record.tax_amount.amount
        )
        summary['tax_jpy'] = Money(
            summary['tax_jpy'].amount + record.tax_jpy.amount,
            Currency.JPY
        )

    def _print_account_summaries(self, account_summary: Dict[str, Dict[str, Money]]) -> None:
        """アカウント別の集計を出力"""
        print("\n=== Account Summary ===")
        for account, summary in account_summary.items():
            print(f"\nAccount: {account}")
            self._print_summary_details(summary)

    def _print_total_summary(self, account_summary: Dict[str, Dict[str, Money]]) -> None:
        """総合計を出力"""
        totals = self._create_empty_summary()
        
        for summary in account_summary.values():
            for key, value in summary.items():
                totals[key] = Money(
                    totals[key].amount + value.amount,
                    value.currency
                )
        
        print("\n=== Total Summary ===")
        self._print_summary_details(totals)

    def _print_summary_details(self, summary: Dict[str, Money]) -> None:
        """集計の詳細を出力"""
        if summary['principal'].amount > 0:
            print(f"CD Principal: ${self._format_money(summary['principal'])}")
        
        if summary['cd_interest'].amount > 0:
            print(
                f"CD Interest Total: ${self._format_money(summary['cd_interest'])} "
                f"(¥{self._format_money(summary['cd_interest_jpy'], 0)})"
            )
        
        print(
            f"Dividend Total: ${self._format_money(summary['dividend'])} "
            f"(¥{self._format_money(summary['dividend_jpy'], 0)})"
        )
        
        print(
            f"Other Interest Total: ${self._format_money(summary['interest'])} "
            f"(¥{self._format_money(summary['interest_jpy'], 0)})"
        )
        
        print(
            f"Withholding Tax Total: ${self._format_money(summary['tax'])} "
            f"(¥{self._format_money(summary['tax_jpy'], 0)})"
        )
        
        # 総収入の計算
        total_income = Money(
            summary['dividend'].amount +
            summary['interest'].amount +
            summary['cd_interest'].amount
        )
        total_income_jpy = Money(
            summary['dividend_jpy'].amount +
            summary['interest_jpy'].amount +
            summary['cd_interest_jpy'].amount,
            Currency.JPY
        )
        
        # 手取り額の計算
        net_income = Money(total_income.amount - summary['tax'].amount)
        net_income_jpy = Money(
            total_income_jpy.amount - summary['tax_jpy'].amount,
            Currency.JPY
        )
        
        print(
            f"Net Income Total: ${self._format_money(net_income)} "
            f"(¥{self._format_money(net_income_jpy, 0)})"
        )

class ColorConsoleWriter(ConsoleWriter):
    """カラー対応コンソール出力クラス"""

    # ANSI エスケープシーケンス
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

    def _print_account_summaries(self, account_summary: Dict[str, Dict[str, Money]]) -> None:
        """アカウント別の集計をカラー出力"""
        print(f"\n{self.COLORS['HEADER']}=== Account Summary ==={self.COLORS['END']}")
        for account, summary in account_summary.items():
            print(f"\n{self.COLORS['BOLD']}Account: {account}{self.COLORS['END']}")
            self._print_summary_details(summary)

    def _print_total_summary(self, account_summary: Dict[str, Dict[str, Money]]) -> None:
        """総合計をカラー出力"""
        totals = self._create_empty_summary()
        
        for summary in account_summary.values():
            for key, value in summary.items():
                totals[key] = Money(
                    totals[key].amount + value.amount,
                    value.currency
                )
        
        print(f"\n{self.COLORS['HEADER']}=== Total Summary ==={self.COLORS['END']}")
        self._print_summary_details(totals)

    def _print_summary_details(self, summary: Dict[str, Money]) -> None:
        """集計の詳細をカラー出力"""
        if summary['principal'].amount > 0:
            print(f"{self.COLORS['BLUE']}CD Principal: "
                  f"${self._format_money(summary['principal'])}{self.COLORS['END']}")
        
        if summary['cd_interest'].amount > 0:
            print(
                f"{self.COLORS['GREEN']}CD Interest Total: "
                f"${self._format_money(summary['cd_interest'])} "
                f"(¥{self._format_money(summary['cd_interest_jpy'], 0)})"
                f"{self.COLORS['END']}"
            )
        
        print(
            f"{self.COLORS['GREEN']}Dividend Total: "
            f"${self._format_money(summary['dividend'])} "
            f"(¥{self._format_money(summary['dividend_jpy'], 0)})"
            f"{self.COLORS['END']}"
        )
        
        print(
            f"{self.COLORS['GREEN']}Other Interest Total: "
            f"${self._format_money(summary['interest'])} "
            f"(¥{self._format_money(summary['interest_jpy'], 0)})"
            f"{self.COLORS['END']}"
        )
        
        print(
            f"{self.COLORS['WARNING']}Withholding Tax Total: "
            f"${self._format_money(summary['tax'])} "
            f"(¥{self._format_money(summary['tax_jpy'], 0)})"
            f"{self.COLORS['END']}"
        )
        
        # 総収入と手取り額の計算は通常のメソッドと同じ
        total_income = Money(
            summary['dividend'].amount +
            summary['interest'].amount +
            summary['cd_interest'].amount
        )
        total_income_jpy = Money(
            summary['dividend_jpy'].amount +
            summary['interest_jpy'].amount +
            summary['cd_interest_jpy'].amount,
            Currency.JPY
        )
        
        net_income = Money(total_income.amount - summary['tax'].amount)
        net_income_jpy = Money(
            total_income_jpy.amount - summary['tax_jpy'].amount,
            Currency.JPY
        )
        
        print(
            f"{self.COLORS['BOLD']}Net Income Total: "
            f"${self._format_money(net_income)} "
            f"(¥{self._format_money(net_income_jpy, 0)})"
            f"{self.COLORS['END']}"
        )

class PrettyConsoleWriter(ConsoleWriter):
    """整形されたコンソール出力クラス"""

    def _print_summary_details(self, summary: Dict[str, Money]) -> None:
        """集計の詳細を整形して出力"""
        # 表のヘッダー
        headers = ['Category', 'USD Amount', 'JPY Amount']
        widths = [20, 15, 20]
        
        # 区切り線の作成
        separator = '+' + '+'.join('-' * width for width in widths) + '+'
        
        # ヘッダーの出力
        print(separator)
        header_format = '|{:^20}|{:^15}|{:^20}|'
        print(header_format.format(*headers))
        print(separator)
        
        # データ行のフォーマット
        row_format = '|{:<20}|{:>15}|{:>20}|'
        
        # 各カテゴリーの出力
        if summary['principal'].amount > 0:
            self._print_row(row_format, 'CD Principal',
                          summary['principal'], None)

        if summary['cd_interest'].amount > 0:
            self._print_row(row_format, 'CD Interest',
                          summary['cd_interest'], summary['cd_interest_jpy'])

        self._print_row(row_format, 'Dividends',
                       summary['dividend'], summary['dividend_jpy'])
        self._print_row(row_format, 'Other Interest',
                       summary['interest'], summary['interest_jpy'])
        self._print_row(row_format, 'Withholding Tax',
                       summary['tax'], summary['tax_jpy'])
        
        print(separator)
        
        # 総計の出力
        total_income = Money(
            summary['dividend'].amount +
            summary['interest'].amount +
            summary['cd_interest'].amount
        )
        total_income_jpy = Money(
            summary['dividend_jpy'].amount +
            summary['interest_jpy'].amount +
            summary['cd_interest_jpy'].amount,
            Currency.JPY
        )
        
        net_income = Money(total_income.amount - summary['tax'].amount)
        net_income_jpy = Money(
            total_income_jpy.amount - summary['tax_jpy'].amount,
            Currency.JPY
        )
        
        self._print_row(row_format, 'Net Income',
                       net_income, net_income_jpy)
        print(separator)

    def _print_row(self, format_str: str, label: str,
                  usd_amount: Money, jpy_amount: Optional[Money]) -> None:
        """表の1行を出力"""
        usd_str = f"${self._format_money(usd_amount)}"
        jpy_str = (f"¥{self._format_money(jpy_amount, 0)}"
                  if jpy_amount else '')
        print(format_str.format(label, usd_str, jpy_str))
