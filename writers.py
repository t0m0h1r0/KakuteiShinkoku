from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List
import csv

from config import CSV_ENCODING
from models import DividendRecord


class ReportWriter(ABC):
    """レポート出力の基底クラス"""
    
    @abstractmethod
    def write(self, records: List[DividendRecord]) -> None:
        """レポートを出力する"""
        pass


class CSVReportWriter(ReportWriter):
    """CSV形式でレポートを出力するクラス"""

    def __init__(self, filename: str):
        self.filename = filename

    def write(self, records: List[DividendRecord]) -> None:
        """CSVファイルにレポートを出力"""
        fieldnames = [
            'date', 'account', 'symbol', 'description', 'type',
            'principal', 'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ]
        
        with Path(self.filename).open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(self._format_record(record))

    @staticmethod
    def _format_record(record: DividendRecord) -> Dict:
        """配当記録をCSV出力用に整形"""
        return {
            'date': record.date,
            'account': record.account,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.type,
            'principal': round(record.principal, 2) if record.principal else '',
            'gross_amount_usd': round(record.gross_amount, 2),
            'tax_usd': round(record.tax, 2),
            'net_amount_usd': record.net_amount_usd,
            'exchange_rate': record.exchange_rate,
            'gross_amount_jpy': record.gross_amount_jpy,
            'tax_jpy': record.tax_jpy,
            'net_amount_jpy': record.net_amount_jpy,
            'reinvested': 'Yes' if record.reinvested else 'No'
        }


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
            'cd_interest_usd': Decimal('0'),
            'tax_usd': Decimal('0'),
            'dividend_jpy': Decimal('0'),
            'interest_jpy': Decimal('0'),
            'cd_interest_jpy': Decimal('0'),
            'tax_jpy': Decimal('0'),
            'principal_usd': Decimal('0')
        }

    @staticmethod
    def _update_summary(summary: Dict, record: DividendRecord) -> None:
        """集計を更新"""
        if record.type == 'CD Interest':
            summary['cd_interest_usd'] += record.gross_amount
            summary['cd_interest_jpy'] += record.gross_amount_jpy
            summary['principal_usd'] += record.principal
        elif record.type == 'Dividend':
            summary['dividend_usd'] += record.gross_amount
            summary['dividend_jpy'] += record.gross_amount_jpy
        else:
            summary['interest_usd'] += record.gross_amount
            summary['interest_jpy'] += record.gross_amount_jpy
        
        summary['tax_usd'] += record.tax
        summary['tax_jpy'] += record.tax_jpy

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
        if summary['principal_usd'] > 0:
            print(f"CD運用元本: ${summary['principal_usd']:,.2f}")
        if summary['cd_interest_usd'] > 0:
            print(f"CD利子合計: ${summary['cd_interest_usd']:,.2f} (¥{int(summary['cd_interest_jpy']):,})")
        print(f"配当金合計: ${summary['dividend_usd']:,.2f} (¥{int(summary['dividend_jpy']):,})")
        print(f"その他利子合計: ${summary['interest_usd']:,.2f} (¥{int(summary['interest_jpy']):,})")
        print(f"源泉徴収合計: ${summary['tax_usd']:,.2f} (¥{int(summary['tax_jpy']):,})")
        
        total_income_usd = summary['dividend_usd'] + summary['interest_usd'] + summary['cd_interest_usd']
        total_income_jpy = summary['dividend_jpy'] + summary['interest_jpy'] + summary['cd_interest_jpy']
        net_usd = total_income_usd - summary['tax_usd']
        net_jpy = total_income_jpy - summary['tax_jpy']
        print(f"手取り合計: ${net_usd:,.2f} (¥{int(net_jpy):,})")


class SymbolSummaryWriter(ReportWriter):
    """シンボル別サマリーをCSV形式で出力するクラス"""
    
    def __init__(self, filename: str):
        self.filename = filename

    def write(self, records: List[DividendRecord]) -> None:
        """シンボル別サマリーをCSVファイルに出力"""
        symbol_summary = self._create_symbol_summary(records)
        self._write_to_csv(symbol_summary)

    def _create_symbol_summary(self, records: List[DividendRecord]) -> List[Dict]:
        """シンボル別の集計を作成"""
        summary_dict: Dict[str, Dict] = {}
        
        for record in records:
            symbol_key = record.symbol if record.symbol else record.description
            
            if symbol_key not in summary_dict:
                summary_dict[symbol_key] = {
                    'symbol': symbol_key,
                    'description': record.description,
                    'type': record.type,
                    'principal': Decimal('0'),
                    'gross_amount_usd': Decimal('0'),
                    'tax_usd': Decimal('0'),
                    'gross_amount_jpy': Decimal('0'),
                    'tax_jpy': Decimal('0'),
                    'transaction_count': 0
                }
            
            summary = summary_dict[symbol_key]
            summary['transaction_count'] += 1
            summary['principal'] += record.principal
            summary['gross_amount_usd'] += record.gross_amount
            summary['gross_amount_jpy'] += record.gross_amount_jpy
            summary['tax_usd'] += record.tax
            summary['tax_jpy'] += record.tax_jpy

        return sorted(
            summary_dict.values(),
            key=lambda x: x['gross_amount_usd'],
            reverse=True
        )

    def _write_to_csv(self, summary_data: List[Dict]) -> None:
        """サマリーデータをCSVファイルに出力"""
        fieldnames = [
            'symbol', 'description', 'type', 'principal',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'transaction_count'
        ]
        
        with Path(self.filename).open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for summary in summary_data:
                net_usd = summary['gross_amount_usd'] - summary['tax_usd']
                net_jpy = summary['gross_amount_jpy'] - summary['tax_jpy']
                
                writer.writerow({
                    'symbol': summary['symbol'],
                    'description': summary['description'],
                    'type': summary['type'],
                    'principal': round(summary['principal'], 2) if summary['principal'] else '',
                    'gross_amount_usd': round(summary['gross_amount_usd'], 2),
                    'tax_usd': round(summary['tax_usd'], 2),
                    'net_amount_usd': round(net_usd, 2),
                    'gross_amount_jpy': round(summary['gross_amount_jpy']),
                    'tax_jpy': round(summary['tax_jpy']),
                    'net_amount_jpy': round(net_jpy),
                    'transaction_count': summary['transaction_count']
                })