from pathlib import Path
from typing import List
import logging
import csv

from ..core.types.transaction import Transaction
from ..app.context import ApplicationContext
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
        self.context.writers['trade_csv'].write(
            [self._format_trade_record(r) for r in trade_records]
        )
        
        # コンソール出力
        self.context.writers['console'].write(dividend_records)

    def _write_profit_loss_summary(self, dividend_records, trade_records):
        """損益サマリーの出力"""
        # 配当収入の集計
        total_dividend_usd = sum(r.gross_amount.amount - r.tax_amount.amount for r in dividend_records)
        total_dividend_jpy = sum((r.gross_amount.amount - r.tax_amount.amount) * r.exchange_rate for r in dividend_records)

        # 取引損益の集計（簡易的な方法）
        total_realized_gain_usd = sum(r.realized_gain.amount for r in trade_records if hasattr(r, 'realized_gain'))
        total_realized_gain_jpy = sum(r.realized_gain.amount * r.exchange_rate for r in trade_records if hasattr(r, 'realized_gain'))

        # サマリーデータの作成
        summary_data = [
            {
                'Category': 'Dividend Income (USD)',
                'Amount': f'{total_dividend_usd:.2f}'
            },
            {
                'Category': 'Dividend Income (JPY)',
                'Amount': f'{total_dividend_jpy:.2f}'
            },
            {
                'Category': 'Realized Gain/Loss (USD)',
                'Amount': f'{total_realized_gain_usd:.2f}'
            },
            {
                'Category': 'Realized Gain/Loss (JPY)',
                'Amount': f'{total_realized_gain_jpy:.2f}'
            },
            {
                'Category': 'Total Income (USD)',
                'Amount': f'{total_dividend_usd + total_realized_gain_usd:.2f}'
            },
            {
                'Category': 'Total Income (JPY)',
                'Amount': f'{total_dividend_jpy + total_realized_gain_jpy:.2f}'
            }
        ]

        # CSV出力
        summary_path = settings.OUTPUT_FILES.get('profit_loss_summary', Path('output/profit_loss_summary.csv'))
        
        try:
            with summary_path.open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['Category', 'Amount'])
                writer.writeheader()
                writer.writerows(summary_data)
            
            self.logger.info(f"Profit/Loss summary written to {summary_path}")
        
        except Exception as e:
            self.logger.error(f"Error writing profit/loss summary: {e}")

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

    def _format_trade_record(self, record):
        """取引記録のフォーマット"""
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