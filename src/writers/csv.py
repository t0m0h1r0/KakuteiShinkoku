from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional
import csv
import logging
import re
from datetime import date
from collections import defaultdict

from src.core.models import DividendRecord, TradeRecord, Money
from src.config.constants import Currency
from .base import BaseWriter, Record, WriterError

class CSVWriter(BaseWriter):
    """CSV出力の基底クラス"""
    
    def __init__(self, filename: Path, fieldnames: List[str]):
        super().__init__()
        self.filename = filename
        self.fieldnames = fieldnames

    def write(self, records: List[Record]) -> None:
        """レコードをCSVファイルに出力"""
        try:
            self._ensure_output_dir(self.filename)
            with self.filename.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                sorted_records = self._sort_records(records)
                for record in sorted_records:
                    writer.writerow(self._format_record(record))
        except Exception as e:
            raise WriterError(f"CSV writing error: {e}")

    def _sort_records(self, records: List[Record]) -> List[Record]:
        """レコードをソート"""
        return sorted(
            records,
            key=lambda x: getattr(x, 'record_date', getattr(x, 'trade_date', None))
        )

    @abstractmethod
    def _format_record(self, record: Record) -> Dict[str, Any]:
        """レコードをCSV出力用に整形"""
        pass

class TradeHistoryWriter(CSVWriter):
    """取引履歴出力クラス"""
    
    def __init__(self, filename: Path):
        super().__init__(filename, [
            'date', 'account', 'symbol', 'description', 'type', 'action',
            'quantity', 'price', 'fees', 'cost_basis_usd', 'proceeds_usd',
            'realized_gain_usd', 'exchange_rate', 'cost_basis_jpy',
            'proceeds_jpy', 'realized_gain_jpy', 'holding_period'
        ])

    def _format_record(self, record: TradeRecord) -> Dict[str, Any]:
        """取引記録をCSV出力用に整形"""
        return {
            'date': record.trade_date.strftime('%Y-%m-%d'),
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.trade_type,
            'action': record.action,
            'quantity': f"{record.quantity:,.0f}",
            'price': self._format_money(record.price),
            'fees': self._format_money(record.fees),
            'cost_basis_usd': self._format_money(record.cost_basis),
            'proceeds_usd': self._format_money(record.proceeds),
            'realized_gain_usd': self._format_money(record.realized_gain),
            'exchange_rate': f"{record.exchange_rate:.2f}",
            'cost_basis_jpy': self._format_money(record.cost_basis_jpy, 0),
            'proceeds_jpy': self._format_money(record.proceeds_jpy, 0),
            'realized_gain_jpy': self._format_money(record.realized_gain_jpy, 0),
            'holding_period': (f"{record.holding_period_days} days" 
                             if record.holding_period_days else '')
        }

class DividendSummaryWriter(CSVWriter):
    """配当サマリー出力クラス"""
    
    def __init__(self, filename: Path):
        super().__init__(filename, [
            'symbol', 'description', 'type', 'principal',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'transaction_count'
        ])

    def write(self, records: List[Record]) -> None:
        """レコードをCSVファイルに出力"""
        try:
            self._ensure_output_dir(self.filename)
            with self.filename.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                
                # レコードを集計
                summary_records = self._aggregate_records(records)
                
                # 集計されたレコードを出力
                for record in sorted(summary_records, key=lambda x: x['description']):
                    writer.writerow(record)
        except Exception as e:
            raise WriterError(f"CSV writing error: {e}")

    def _format_record(self, record: DividendRecord) -> Dict[str, Any]:
        """レコードをCSV出力用に整形"""
        net_amount_usd = record.gross_amount.amount - record.tax_amount.amount
        net_amount_jpy = record.gross_amount_jpy.amount - record.tax_jpy.amount
        
        return {
            'symbol': record.symbol,
            'description': record.description,
            'type': record.income_type,
            'principal': self._format_money(record.principal_amount),
            'gross_amount_usd': self._format_money(record.gross_amount),
            'tax_usd': self._format_money(record.tax_amount),
            'net_amount_usd': self._format_money(Money(net_amount_usd)),
            'gross_amount_jpy': self._format_money(record.gross_amount_jpy, 0),
            'tax_jpy': self._format_money(record.tax_jpy, 0),
            'net_amount_jpy': self._format_money(Money(net_amount_jpy, Currency.JPY), 0),
            'transaction_count': '1'
        }

    def _aggregate_records(self, records: List[DividendRecord]) -> List[Dict[str, Any]]:
        """レコードを集計"""
        summary_dict = {}
        
        for record in records:
            # descriptionから日付部分を除去
            base_description = self._normalize_description(record.description)
            
            # キーを生成（symbolが空の場合はdescriptionを使用）
            key = (base_description, record.income_type)
            
            if key not in summary_dict:
                summary_dict[key] = {
                    'symbol': record.symbol,
                    'description': base_description,
                    'type': record.income_type,
                    'principal': record.principal_amount.amount,
                    'gross_amount_usd': record.gross_amount.amount,
                    'tax_usd': record.tax_amount.amount,
                    'net_amount_usd': record.net_amount_usd.amount,
                    'gross_amount_jpy': record.gross_amount_jpy.amount,
                    'tax_jpy': record.tax_jpy.amount,
                    'net_amount_jpy': record.net_amount_jpy.amount,
                    'transaction_count': 1
                }
            else:
                summary = summary_dict[key]
                summary['principal'] += record.principal_amount.amount
                summary['gross_amount_usd'] += record.gross_amount.amount
                summary['tax_usd'] += record.tax_amount.amount
                summary['net_amount_usd'] += record.net_amount_usd.amount
                summary['gross_amount_jpy'] += record.gross_amount_jpy.amount
                summary['tax_jpy'] += record.tax_jpy.amount
                summary['net_amount_jpy'] += record.net_amount_jpy.amount
                summary['transaction_count'] += 1

        # 集計結果をフォーマット
        formatted_records = []
        for summary in summary_dict.values():
            formatted_records.append({
                'symbol': summary['symbol'],
                'description': summary['description'],
                'type': summary['type'],
                'principal': self._format_money(Money(summary['principal'])),
                'gross_amount_usd': self._format_money(Money(summary['gross_amount_usd'])),
                'tax_usd': self._format_money(Money(summary['tax_usd'])),
                'net_amount_usd': self._format_money(Money(summary['net_amount_usd'])),
                'gross_amount_jpy': self._format_money(Money(summary['gross_amount_jpy'], 'JPY'), 0),
                'tax_jpy': self._format_money(Money(summary['tax_jpy'], 'JPY'), 0),
                'net_amount_jpy': self._format_money(Money(summary['net_amount_jpy'], 'JPY'), 0),
                'transaction_count': summary['transaction_count']
            })

        return formatted_records

    def _normalize_description(self, description: str) -> str:
        """説明文から日付部分を除去して正規化"""
        date_patterns = [
            r'\d{2}/\d{2}/\d{2,4}',                  
            r'\d{2}-\d{2}-\d{2,4}',                  
            r'\d{2}/\d{2}-\d{2}/\d{2}',             
            r'\d{2}/\d{2}/\d{2,4}-\d{2}/\d{2}/\d{2,4}'  
        ]
        
        normalized = description
        
        for pattern in date_patterns:
            normalized = re.sub(pattern, '', normalized)
        
        keywords_to_remove = ['MATURED', '**MATURED**']
        for keyword in keywords_to_remove:
            normalized = normalized.replace(keyword, '')
        
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()

class DividendHistoryWriter(CSVWriter):
    """配当履歴出力クラス"""
    
    def __init__(self, filename: Path):
        super().__init__(filename, [
            'date', 'account', 'symbol', 'description', 'type',
            'principal', 'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ])

    def _format_record(self, record: DividendRecord) -> Dict[str, Any]:
        """配当記録をCSV出力用に整形"""
        return {
            'date': record.record_date.strftime('%Y-%m-%d'),
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.income_type,
            'principal': self._format_money(record.principal_amount),
            'gross_amount_usd': self._format_money(record.gross_amount),
            'tax_usd': self._format_money(record.tax_amount),
            'net_amount_usd': self._format_money(record.net_amount_usd),
            'exchange_rate': f"{record.exchange_rate:.2f}",
            'gross_amount_jpy': self._format_money(record.gross_amount_jpy, 0),
            'tax_jpy': self._format_money(record.tax_jpy, 0),
            'net_amount_jpy': self._format_money(record.net_amount_jpy, 0),
            'reinvested': 'Yes' if record.is_reinvested else 'No'
        }

class OptionPremiumWriter(CSVWriter):
    """オプションプレミアム出力クラス（改善版）"""
    
    def __init__(self, filename: Path):
        super().__init__(filename, [
            'date', 'symbol', 'description', 'action', 'status',
            'quantity', 'premium_usd', 'fees_usd', 'net_premium_usd',
            'exchange_rate', 'premium_jpy', 'fees_jpy', 'net_premium_jpy',
            'cumulative_realized_usd', 'cumulative_unrealized_usd',
            'cumulative_total_usd', 'holding_period_days'
        ])

    def write(self, records: List[dict]) -> None:
        """レコードをCSVファイルに出力"""
        try:
            self._ensure_output_dir(self.filename)
            with self.filename.open('w', newline='', encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=self.fieldnames)
                writer.writeheader()
                
                # 累積値の計算
                cumulative_realized = Decimal('0')
                cumulative_unrealized = Decimal('0')
                
                for record in self._sort_records(records):
                    if record['status'] == 'OPEN':
                        cumulative_unrealized += record['net_premium']
                    else:  # CLOSED
                        cumulative_realized += record['net_premium']
                        cumulative_unrealized -= (record['premium'] - record['fees'])
                    
                    writer.writerow(self._format_record(record, 
                                                      cumulative_realized,
                                                      cumulative_unrealized))
            
            self._logger.info(f"Successfully wrote {len(records)} records to {self.filename}")
            
        except Exception as e:
            error_msg = f"Failed to write option premium records: {e}"
            self._logger.error(error_msg)
            raise WriterError(error_msg)

    def _sort_records(self, records: List[dict]) -> List[dict]:
        """レコードを日付でソート"""
        return sorted(records, key=lambda x: x['date'])

    def _format_record(self, record: dict, 
                      cumulative_realized: Decimal,
                      cumulative_unrealized: Decimal) -> Dict[str, str]:
        """オプションプレミアム記録をCSV出力用に整形"""
        exchange_rate = self._get_exchange_rate(record['date'])
        holding_period = ''
        
        if record['status'] == 'CLOSED':
            # 保有期間を計算（オープンポジションがある場合のみ）
            if 'open_date' in record:
                holding_period = (record['date'] - record['open_date']).days
        
        return {
            'date': record['date'].strftime('%Y-%m-%d'),
            'symbol': record['symbol'],
            'description': record['description'],
            'action': record['action'],
            'status': record['status'],
            'quantity': str(record['quantity']),
            'premium_usd': self._format_money(Money(record['premium'])),
            'fees_usd': self._format_money(Money(record['fees'])),
            'net_premium_usd': self._format_money(Money(record['net_premium'])),
            'exchange_rate': f"{exchange_rate:.2f}",
            'premium_jpy': self._format_money(
                Money(record['premium'] * exchange_rate, Currency.JPY), 0),
            'fees_jpy': self._format_money(
                Money(record['fees'] * exchange_rate, Currency.JPY), 0),
            'net_premium_jpy': self._format_money(
                Money(record['net_premium'] * exchange_rate, Currency.JPY), 0),
            'cumulative_realized_usd': self._format_money(Money(cumulative_realized)),
            'cumulative_unrealized_usd': self._format_money(Money(cumulative_unrealized)),
            'cumulative_total_usd': self._format_money(
                Money(cumulative_realized + cumulative_unrealized)),
            'holding_period_days': str(holding_period) if holding_period != '' else ''
        }

    def write_summary(self, summary: dict) -> None:
        """サマリー情報を別ファイルに出力"""
        summary_file = self.filename.parent / 'option_premium_summary.txt'
        
        try:
            with summary_file.open('w', encoding=self.encoding) as f:
                f.write("=== Option Premium Summary ===\n\n")
                
                # 取引概要
                f.write("Transaction Summary:\n")
                f.write(f"- Total Trades: {summary['transaction_count']}\n")
                f.write(f"- Total Contracts: {summary['total_contracts']}\n")
                f.write(f"- Active Contracts: {summary['active_contracts']}\n")
                f.write(f"- Expired Contracts: {summary['expired_contracts']}\n")
                f.write(f"- Assigned Contracts: {summary['assigned_contracts']}\n\n")
                
                # プレミアム概要（USD）
                f.write("Premium Summary (USD):\n")
                f.write(f"- Total Premium Income: ${self._format_money(Money(summary['total_premium']))}\n")
                f.write(f"- Total Fees: ${self._format_money(Money(summary['total_fees']))}\n")
                f.write(f"- Net Premium Income: ${self._format_money(Money(summary['net_premium']))}\n")
                f.write(f"- Realized Premium: ${self._format_money(Money(summary['realized_premium']))}\n")
                f.write(f"- Unrealized Premium: ${self._format_money(Money(summary['unrealized_premium']))}\n")
                
                if summary['transaction_count'] > 0:
                    f.write(f"- Average Net Premium per Trade: "
                           f"${self._format_money(Money(summary['average_premium']))}\n")
                
                # 現在のポジション状況
                f.write(f"\nCurrent Status:\n")
                f.write(f"- Open Positions: {summary['open_positions']}\n")
                f.write(f"- Active Contracts: {summary['active_contracts']}\n")
                
            self._logger.info(f"Successfully wrote summary to {summary_file}")
            
        except Exception as e:
            error_msg = f"Failed to write summary: {e}"
            self._logger.error(error_msg)
            raise WriterError(error_msg)