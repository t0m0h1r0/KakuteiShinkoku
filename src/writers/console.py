from typing import List, Dict
from decimal import Decimal

from ..models.dividend import DividendRecord
from .base import ReportWriter

class ConsoleReportWriter(ReportWriter):
    """コンソールにレポートを出力するクラス"""

    def write(self, records: List[DividendRecord]) -> None:
        """アカウント別サマリーと総合計を出力"""
        account_summary = self._create_account_summary(records)
        self._print_account_summaries(account_summary)
        self._print_total_summary(account_summary)

    def _create_account_summary(self, records: List[DividendRecord]) -> Dict:
        """アカウント別の集計を作成"""
        summary = {}
        for record in records:
            if record.account not in summary:
                summary[record.account] = self._create_empty_summary()
            
            self._update_summary(summary[record.account], record)
        return summary

    @staticmethod
    def _create_empty_summary() -> Dict:
        """新しい集計辞書を作成"""
        return {
            'dividend_usd': Decimal('0'),
            'interest_usd': Decimal('0'),
            'tax_usd': Decimal('0'),
            'dividend_jpy': Decimal('0'),
            'interest_jpy': Decimal('0'),
            'tax_jpy': Decimal('0')
        }

    @staticmethod
    def _update_summary(summary: Dict, record: DividendRecord) -> None:
        """集計を更新"""
        if record.type == 'Dividend':
            summary['dividend_usd'] += record.gross_amount
            summary['dividend_jpy'] += record.gross_amount * record.exchange_rate
        else:
            summary['interest_usd'] += record.gross_amount
            summary['interest_jpy'] += record.gross_amount * record.exchange_rate
        summary['tax_usd'] += record.tax
        summary['tax_jpy'] += record.tax * record.exchange_rate

    def _print_account_summaries(self, account_summary: Dict) -> None:
        """アカウント別の集計を出力"""
        print("\n=== アカウント別集計 ===")
        for account, summary in account_summary.items():
            print(f"\nアカウント: {account}")
            self._print_summary_details(summary)

    def _print_total_summary(self, account_summary: Dict) -> None:
        """総合計を出力"""
        totals = {
            key: sum(s[key] for s in account_summary.values())
            for key in self._create_empty_summary().keys()
        }
        
        print("\n=== 総合計 ===")
        self._print_summary_details(totals)

    @staticmethod
    def _print_summary_details(summary: Dict) -> None:
        """集計の詳細を出力"""
        print(f"配当金合計: ${summary['dividend_usd']:,.2f} (¥{int(summary['dividend_jpy']):,})")
        print(f"利子合計: ${summary['interest_usd']:,.2f} (¥{int(summary['interest_jpy']):,})")
        print(f"源泉徴収合計: ${summary['tax_usd']:,.2f} (¥{int(summary['tax_jpy']):,})")
        
        net_usd = summary['dividend_usd'] + summary['interest_usd'] - summary['tax_usd']
        net_jpy = summary['dividend_jpy'] + summary['interest_jpy'] - summary['tax_jpy']
        print(f"手取り合計: ${net_usd:,.2f} (¥{int(net_jpy):,})")
