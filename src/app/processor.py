from pathlib import Path
from typing import List, Dict, Any
import logging
import csv
from collections import defaultdict
from decimal import Decimal
import re

from ..core.types.transaction import Transaction
from .context import ApplicationContext
from ..config import settings

class InvestmentDataProcessor:
    """投資データ処理の主制御クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(__name__)

    def process_files(self, data_dir: Path) -> bool:
        """ファイル処理のメインフロー"""
        try:
            # JSONファイルの検索
            json_files = list(data_dir.glob('*.json'))
            if not json_files:
                self.logger.error("No JSON files found for processing")
                return False

            # トランザクションの処理
            all_transactions = self._load_transactions(json_files)
            if not all_transactions:
                return False

            # レコードの生成
            dividend_records = self.context.dividend_processor.process_all(all_transactions)
            trade_records = self.context.trade_processor.process_all(all_transactions)

            # レポート出力
            self._write_reports(dividend_records, trade_records)
            
            # 損益サマリーの出力
            self._write_profit_loss_summary(dividend_records, trade_records)
            
            return True

        except Exception as e:
            self.logger.error(f"Processing error: {e}", exc_info=True)
            return False

    def _load_transactions(self, json_files: List[Path]) -> List[Transaction]:
        """トランザクションの読み込み"""
        all_transactions = []
        for file in json_files:
            self.logger.info(f"Processing file: {file}")
            transactions = self.context.transaction_loader.load(file)
            all_transactions.extend(transactions)
        return all_transactions

    def _write_reports(self, dividend_records, trade_records):
        """レポートの出力"""
        # CSV出力
        self.context.writers['dividend_csv'].write(
            [self._format_dividend_record(r) for r in dividend_records]
        )

        # 株式取引と取引オプション取引を分離
        stock_trades = [r for r in trade_records if r.trade_type != 'Option']
        option_trades = [r for r in trade_records if r.trade_type == 'Option']

        # 株式取引とオプション取引を別々に出力
        self.context.writers['stock_trade_csv'].write(
            [self._format_trade_record(r, 'stock') for r in stock_trades]
        )
        self.context.writers['option_trade_csv'].write(
            [self._format_trade_record(r, 'option') for r in option_trades]
        )
        
        # コンソール出力
        self.context.writers['console'].write(dividend_records)

    def _write_profit_loss_summary(self, dividend_records, trade_records):
        """詳細な損益サマリーの出力"""
        # 損益サマリーを生成
        detailed_summary = self._generate_detailed_profit_loss_summary(dividend_records, trade_records)
        
        # サマリーをCSV出力
        summary_path = settings.OUTPUT_FILES.get('detailed_profit_loss_summary', Path('output/detailed_profit_loss_summary.csv'))
        
        try:
            # ディレクトリが存在しない場合は作成
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            
            with summary_path.open('w', newline='', encoding='utf-8') as f:
                # データがない場合は空のファイルを作成
                if not detailed_summary:
                    return
                
                # ヘッダーはデータの最初の辞書のキーを使用
                fieldnames = ['Symbol', 'Type', 'Gain or Loss (USD)', 'Tax (USD)', 'Rate(USDJPY)', 'Gain or Loss (JPY)', 'Tax (JPY)', 'Count']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                writer.writeheader()
                writer.writerows(detailed_summary)
            
            self.logger.info(f"Detailed profit/loss summary written to {summary_path}")
        
        except Exception as e:
            self.logger.error(f"Error writing detailed summary to {summary_path}: {e}")

    def _generate_detailed_profit_loss_summary(self, dividend_records, trade_records) -> List[Dict[str, Any]]:
        """詳細な損益サマリーを生成"""
        # オプションを解析して基本シンボルを抽出する関数
        def extract_option_base_symbol(symbol):
            """オプションシンボルから基本シンボルを抽出"""
            try:
                # U 03/17/2023 25.00 P のような形式を想定
                # 正規表現でシンボル部分を抽出
                match = re.match(r'^(\w+)', symbol)
                if match:
                    return match.group(1)
                return symbol
            except Exception:
                return symbol

        # シンボルと種別ごとに集計するための辞書
        summary_dict = defaultdict(lambda: {
            'Gain or Loss (USD)': Decimal('0'),
            'Tax (USD)': Decimal('0'),
            'Rate(USDJPY)': Decimal('0'),
            'Gain or Loss (JPY)': Decimal('0'),
            'Tax (JPY)': Decimal('0'),
            'Count': 0
        })

        # 配当・利子収入の集計
        for record in dividend_records:
            key = (record.symbol or 'Unknown', record.income_type)
            summary = summary_dict[key]
            
            summary['Gain or Loss (USD)'] += record.gross_amount.amount
            summary['Tax (USD)'] += record.tax_amount.amount
            summary['Rate(USDJPY)'] = record.exchange_rate  # 最後の為替レートを使用
            summary['Gain or Loss (JPY)'] += record.gross_amount.amount * record.exchange_rate
            summary['Tax (JPY)'] += record.tax_amount.amount * record.exchange_rate
            summary['Count'] += 1

        # 取引損益の集計
        for record in trade_records:
            if hasattr(record, 'realized_gain'):
                # オプションの場合は特別な処理
                if record.trade_type == 'Option':
                    symbol = extract_option_base_symbol(record.symbol)
                    key = (symbol, 'Option')
                else:
                    key = (record.symbol or 'Unknown', record.trade_type)
                
                summary = summary_dict[key]
                
                summary['Gain or Loss (USD)'] += record.realized_gain.amount
                summary['Tax (USD)'] += Decimal('0')
                summary['Rate(USDJPY)'] = record.exchange_rate  # 最後の為替レートを使用
                summary['Gain or Loss (JPY)'] += record.realized_gain.amount * record.exchange_rate
                summary['Tax (JPY)'] += Decimal('0')
                summary['Count'] += 1

        # 結果を整形
        detailed_summary = []
        for (symbol, type_), amounts in summary_dict.items():
            # ゼロでないエントリーのみ追加
            if amounts['Count'] > 0:
                summary_entry = {
                    'Symbol': symbol,
                    'Type': type_,
                    'Gain or Loss (USD)': f"{amounts['Gain or Loss (USD)']:.2f}",
                    'Tax (USD)': f"{amounts['Tax (USD)']:.2f}",
                    'Rate(USDJPY)': f"{amounts['Rate(USDJPY)']:.2f}",
                    'Gain or Loss (JPY)': f"{amounts['Gain or Loss (JPY)']:.2f}",
                    'Tax (JPY)': f"{amounts['Tax (JPY)']:.2f}",
                    'Count': amounts['Count']
                }
                detailed_summary.append(summary_entry)

        return detailed_summary

    def _format_trade_record(self, record, trade_type='stock'):
        """取引記録のフォーマット"""
        if trade_type == 'stock':
            return {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'type': record.trade_type,
                'action': record.action,
                'quantity': record.quantity,
                'price': record.price.amount
            }
        elif trade_type == 'option':
            # オプション取引の詳細フォーマット
            # シンボル解析
            option_details = self._parse_option_symbol(record.symbol)
            
            # 売りか買いかを判定
            position_type = 'Short' if 'SELL' in record.action.upper() else 'Long'
            
            # 期限切れの場合の特別処理
            is_expired = record.action.upper() == 'EXPIRED'
            
            return {
                'date': record.trade_date,
                'account': record.account_id,
                'symbol': option_details['base_symbol'],
                'expiry_date': option_details['expiry_date'],
                'strike_price': option_details['strike_price'],
                'option_type': option_details['option_type'],
                'position_type': position_type,
                'description': record.description,
                'action': record.action,
                'quantity': record.quantity,
                'premium_or_gain': record.realized_gain.amount if is_expired else record.price.amount,
                'is_expired': is_expired
            }

    def _parse_option_symbol(self, symbol: str) -> Dict[str, str]:
        """オプションシンボルをパース"""
        # 例: U 03/17/2023 25.00 P
        parts = symbol.split()
        
        return {
            'base_symbol': parts[0],
            'expiry_date': parts[1] if len(parts) > 1 else 'Unknown',
            'strike_price': parts[2] if len(parts) > 2 else 'Unknown',
            'option_type': parts[3] if len(parts) > 3 else 'Unknown'
        }

    def _format_dividend_record(self, record):
        """配当記録のフォーマット"""
        return {
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.income_type,
            'gross_amount': record.gross_amount.amount,
            'tax_amount': record.tax_amount.amount,
            'net_amount': record.gross_amount.amount - record.tax_amount.amount
        }