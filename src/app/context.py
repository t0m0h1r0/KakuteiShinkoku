from pathlib import Path
import logging.config
from typing import Dict, Any, Optional
from decimal import Decimal

from ..config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, OUTPUT_FILES,
    LOGGING_CONFIG
)
from ..exchange.factories import create_rate_provider
from ..processors.transaction_loader import JSONTransactionLoader
from ..processors.dividend import DividendProcessor
from ..processors.trade import TradeProcessor
from ..display.factories import create_display_output
from ..display.formatters.table_formatter import TableFormatter
from ..display.formatters.text_formatter import TextFormatter
from ..display.outputs.csv_writer import CSVWriter

class ApplicationContext:
    """アプリケーションのコンテキスト管理クラス"""
    
    def __init__(self, use_color_output: bool = True):
        # ディレクトリとログの設定
        self._setup_directories()
        self._setup_logging()
        
        # ロガーの初期化
        self.logger = logging.getLogger(__name__)
        
        # 為替レートプロバイダーの初期化
        self.exchange_rate_provider = create_rate_provider(EXCHANGE_RATE_FILE, use_cache=True)
        
        # プロセッサーの初期化
        self.transaction_loader = JSONTransactionLoader()
        self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
        self.trade_processor = TradeProcessor(self.exchange_rate_provider)
        
        # 出力系の初期化
        self.display_outputs = self._setup_display_outputs(use_color_output)
        self.writers = self._setup_writers()
        
        # 処理結果の保存用
        self.processing_results: Optional[Dict[str, Any]] = None

    @staticmethod
    def _setup_logging():
        """ログ設定"""
        logging.config.dictConfig(LOGGING_CONFIG)

    @staticmethod
    def _setup_directories():
        """ディレクトリ構造の設定"""
        for directory in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        if not EXCHANGE_RATE_FILE.exists():
            raise FileNotFoundError(f"Exchange rate file not found: {EXCHANGE_RATE_FILE}")

    def _setup_display_outputs(self, use_color: bool) -> Dict:
        """表示出力の設定"""
        table_formatter = TableFormatter()
        text_formatter = TextFormatter()
        
        return {
            'console': create_display_output(
                'console',
                use_color=use_color,
                formatter=table_formatter
            ),
            'summary_file': create_display_output(
                'file',
                output_path=OUTPUT_FILES['profit_loss_summary'],
                formatter=text_formatter
            ),
            'log_file': create_display_output(
                'log',
                output_path=LOG_DIR / 'processing_summary.log',
                formatter=text_formatter,
                prefix='[SUMMARY] '
            )
        }

    def _setup_writers(self) -> Dict:
        """CSVライターとコンソール出力の設定"""
        return {
            'console': self.display_outputs['console'],
            'dividend_csv': CSVWriter(
                OUTPUT_FILES['dividend_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'gross_amount', 'tax_amount', 'net_amount'
                ]
            ),
            'stock_trade_csv': CSVWriter(
                OUTPUT_FILES['stock_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'action', 'quantity', 'price'
                ]
            ),
            'option_trade_csv': CSVWriter(
                OUTPUT_FILES['option_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'expiry_date',
                    'strike_price', 'option_type', 'position_type',
                    'description', 'action', 'quantity',
                    'premium_or_gain', 'is_expired'
                ]
            ),
            'profit_loss_csv': CSVWriter(
                OUTPUT_FILES['profit_loss_summary'],
                fieldnames=[
                    'Account', 'Dividend', 'Interest', 
                    'CD Interest', 'Tax', 'Net Total'
                ]
            )
        }

    def display_results(self) -> None:
        """処理結果を表示"""
        if not self.processing_results:
            self.logger.warning("No processing results available to display")
            return

        try:
            # 結果をタイプ別に取得
            dividend_records = self.processing_results.get('dividend_records', [])
            trade_records = self.processing_results.get('trade_records', [])

            # サマリーデータの準備
            summary_data = self._prepare_summary_data(dividend_records, trade_records)

            # まずコンソール出力（一度だけ）
            self.display_outputs['console'].output(dividend_records)

            # サマリーファイルとログファイルに出力
            if summary_data:
                # CSVライターを使用して明示的に出力
                account_name = list(summary_data['accounts'].keys())[0]
                summary_record = {
                    'Account': account_name,
                    'Dividend': summary_data['total']['Dividend'],
                    'Interest': summary_data['total']['Interest'],
                    'CD Interest': summary_data['total'].get('CD Interest', Decimal('0')),
                    'Tax': summary_data['total']['Tax'],
                    'Net Total': (
                        summary_data['total']['Dividend'] + 
                        summary_data['total']['Interest'] +
                        summary_data['total'].get('CD Interest', Decimal('0')) - 
                        summary_data['total']['Tax']
                    )
                }

                self.writers['profit_loss_csv'].output([summary_record])

                # ログ用の出力文字列を作成
                log_content = "\n".join([
                    f"Account: {account_name}",
                    f"Dividend: ${summary_record['Dividend']:.2f}",
                    f"Interest: ${summary_record['Interest']:.2f}",
                    f"CD Interest: ${summary_record['CD Interest']:.2f}",
                    f"Tax: ${summary_record['Tax']:.2f}",
                    f"Net Total: ${summary_record['Net Total']:.2f}"
                ])

                # ログファイル出力を文字列で渡す
                try:
                    self.display_outputs['log_file'].output(log_content)
                except Exception:
                    # ログ出力中のエラーを抑制
                    pass
        
        except Exception as e:
            self.logger.error(f"Error displaying results: {e}", exc_info=True)

    def _prepare_summary_data(self, dividend_records, trade_records) -> dict:
        """サマリーデータの準備"""
        # 配当・利子収入の集計
        dividend_summary = {
            'Dividend': sum(r.gross_amount.amount for r in dividend_records if r.income_type == 'Dividend'),
            'Interest': sum(r.gross_amount.amount for r in dividend_records if r.income_type == 'Interest'),
            'CD Interest': sum(r.gross_amount.amount for r in dividend_records if r.income_type == 'CD Interest'),
            'Tax': sum(r.tax_amount.amount for r in dividend_records),
        }

        # 取引損益の集計
        trade_summary = {
            'realized_gain': sum(r.realized_gain.amount for r in trade_records if hasattr(r, 'realized_gain')),
        }

        # アカウントごとの集計を準備
        accounts = {}
        for record in dividend_records:
            if record.account_id not in accounts:
                accounts[record.account_id] = {
                    'Dividend': Decimal('0'),
                    'Interest': Decimal('0'),
                    'CD Interest': Decimal('0'),
                    'Tax': Decimal('0'),
                }
            summary = accounts[record.account_id]
            
            if record.income_type == 'Dividend':
                summary['Dividend'] += record.gross_amount.amount
            elif record.income_type == 'CD Interest':
                summary['CD Interest'] += record.gross_amount.amount
            else:
                summary['Interest'] += record.gross_amount.amount
            summary['Tax'] += record.tax_amount.amount

        return {
            'total': dividend_summary,
            'trade': trade_summary,
            'accounts': accounts
        }

    def cleanup(self) -> None:
        """コンテキストのクリーンアップ"""
        # キャッシュのクリア
        if hasattr(self.exchange_rate_provider, 'clear_cache'):
            self.exchange_rate_provider.clear_cache()
        
        # 結果のクリア
        self.processing_results = None
        
        self.logger.info("Application context cleaned up")