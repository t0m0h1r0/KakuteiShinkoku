from abc import ABC, abstractmethod
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Any, Optional
import csv
import logging
import re  # 正規表現モジュールを追加
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
                for record in sorted(records, key=lambda x: x.record_date):
                    writer.writerow(self._format_record(record))
        except Exception as e:
            raise WriterError(f"CSV writing error: {e}")

    @abstractmethod
    def _format_record(self, record: Record) -> Dict[str, Any]:
        """レコードをCSV出力用に整形"""
        pass

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

class DividendSummaryWriter(CSVWriter):
    """配当サマリー出力クラス"""
    
    def __init__(self, filename: Path):
        super().__init__(filename, [
            'symbol', 'description', 'type', 'principal',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'transaction_count'
        ])

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
        # 日付パターンを定義
        date_patterns = [
            r'\d{2}/\d{2}/\d{2,4}',                  # MM/DD/YY or MM/DD/YYYY
            r'\d{2}-\d{2}-\d{2,4}',                  # MM-DD-YY or MM-DD-YYYY
            r'\d{2}/\d{2}-\d{2}/\d{2}',             # MM/DD-MM/DD
            r'\d{2}/\d{2}/\d{2,4}-\d{2}/\d{2}/\d{2,4}'  # MM/DD/YY-MM/DD/YY
        ]
        
        normalized = description
        
        # 日付パターンを削除
        for pattern in date_patterns:
            normalized = re.sub(pattern, '', normalized)
        
        # "MATURED"など特定のキーワードを削除
        keywords_to_remove = ['MATURED', '**MATURED**']
        for keyword in keywords_to_remove:
            normalized = normalized.replace(keyword, '')
        
        # 余分な空白を削除して整形
        normalized = ' '.join(normalized.split())
        
        return normalized.strip()
                
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