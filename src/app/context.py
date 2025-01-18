from pathlib import Path
import logging.config
from typing import Dict, Any, Optional, List
from decimal import Decimal

from ..config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, OUTPUT_FILES,
    LOGGING_CONFIG
)
from ..exchange.factories import create_rate_provider
from ..processors.transaction_loader import JSONTransactionLoader
from ..processors.dividend_income import DividendProcessor, DividendRecord
from ..processors.interest_income import InterestProcessor, InterestRecord
from ..processors.stock_trade import StockTradeProcessor
from ..processors.option_trade import OptionTradeProcessor
from ..processors.option_premium import OptionPremiumProcessor
from ..display.factories import create_display_output
from ..display.formatters.table_formatter import TableFormatter
from ..display.formatters.text_formatter import TextFormatter
from ..display.outputs.csv_writer import CSVWriter
from ..core.types.transaction import Transaction

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
        
        # 新しいプロセッサーを追加
        self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
        self.interest_processor = InterestProcessor(self.exchange_rate_provider)
        
        self.stock_processor = StockTradeProcessor(self.exchange_rate_provider)
        self.option_processor = OptionTradeProcessor(self.exchange_rate_provider)
        self.premium_processor = OptionPremiumProcessor(self.exchange_rate_provider)
        
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
                formatter=text_formatter
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
            'interest_csv': CSVWriter(
                OUTPUT_FILES['interest_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'gross_amount', 'tax_amount', 'net_amount', 
                    'is_matured'
                ]
            ),
            'stock_trade_csv': CSVWriter(
                OUTPUT_FILES['stock_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'action', 'quantity', 'price', 'realized_gain'
                ]
            ),
            'option_trade_csv': CSVWriter(
                OUTPUT_FILES['option_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'expiry_date',
                    'strike_price', 'option_type', 'position_type',
                    'description', 'action', 'quantity', 'price', 'is_expired'
                ]
            ),
            'option_premium_csv': CSVWriter(
                OUTPUT_FILES['option_premium'],
                fieldnames=[
                    'date', 'account', 'symbol', 'expiry_date',
                    'strike_price', 'option_type', 'premium_amount'
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
            # 各種レコードの取得
            dividend_records = self.processing_results.get('dividend_records', [])
            interest_records = self.processing_results.get('interest_records', [])
            stock_records = self.processing_results.get('stock_records', [])
            option_records = self.processing_results.get('option_records', [])
            premium_records = self.processing_results.get('premium_records', [])

            # デバッグ出力
            print("\n--- 収入レコード詳細 ---")
            print(f"配当レコード数: {len(dividend_records)}")
            print(f"利子レコード数: {len(interest_records)}")
            print("--- 収入レコード詳細 終了 ---\n")

            # サマリーデータの準備
            income_summary = self._calculate_income_summary(
                dividend_records, 
                interest_records  # これを追加
            )
            trading_summary = self._calculate_trading_summary(
                stock_records, option_records, premium_records
            )
            
            total_summary = {
                'total_income': income_summary['net_total'],
                'total_trading': trading_summary['net_total'],
                'grand_total': (
                    income_summary['net_total'] + 
                    trading_summary['net_total']
                )
            }

            # 総合サマリーの作成
            full_summary = {
                'income': income_summary,
                'trading': trading_summary,
                'total': total_summary
            }

            # サマリーファイルに出力
            self.display_outputs['summary_file'].output(full_summary)

            # CSVファイルへの出力
            self._write_summary_to_csv(income_summary, trading_summary)
            
            # ログファイルに出力
            log_content = self._prepare_log_content(income_summary, trading_summary, total_summary)
            self.display_outputs['log_file'].output(log_content)

        except Exception as e:
            self.logger.error(f"Error displaying results: {e}", exc_info=True)

    def _calculate_income_summary(self, 
                                 dividend_records: List[DividendRecord], 
                                 interest_records: List[InterestRecord]) -> Dict:
        """収入サマリーの計算"""
        # デバッグ出力
        print("\n--- 利子レコード詳細 ---")
        for record in interest_records:
            print(f"Income Type: {record.income_type}, Amount: {record.gross_amount.amount}")
        print("--- 利子レコード詳細 終了 ---\n")

        summary = {
            'dividend_total': sum(r.gross_amount.amount for r in dividend_records),
            'interest_total': sum(r.gross_amount.amount for r in interest_records if r.income_type == 'Interest'),
            'cd_interest_total': sum(r.gross_amount.amount for r in interest_records 
                                     if r.income_type in ['CD Interest', 'Bond Interest']),
            'tax_total': sum(r.tax_amount.amount for r in dividend_records + interest_records)
        }
        
        summary['net_total'] = (
            summary['dividend_total'] +
            summary['interest_total'] +
            summary['cd_interest_total'] -
            summary['tax_total']
        )
        
        # デバッグ出力
        print("\n--- 収入サマリー ---")
        print(f"Dividend Total: ${summary['dividend_total']}")
        print(f"Interest Total: ${summary['interest_total']}")
        print(f"CD Interest Total: ${summary['cd_interest_total']}")
        print(f"Tax Total: ${summary['tax_total']}")
        print(f"Net Total: ${summary['net_total']}")
        print("--- 収入サマリー 終了 ---\n")
        
        return summary

    def _calculate_trading_summary(self, 
                                  stock_records: List, 
                                  option_records: List, 
                                  premium_records: List) -> Dict:
        """取引サマリーの計算"""
        summary = {
            'stock_gain': sum(r.realized_gain.amount for r in stock_records),
            'option_gain': sum(r.price.amount for r in option_records if r.action == 'SELL'),
            'premium_income': sum(r.premium_amount.amount for r in premium_records)
        }
        
        summary['net_total'] = (
            summary['stock_gain'] +
            summary['option_gain'] +
            summary['premium_income']
        )
        
        return summary

    def _write_summary_to_csv(self, income_summary: Dict, trading_summary: Dict) -> None:
        """サマリーをCSVに出力"""
        summary_record = {
            'Account': 'ALL',
            'Dividend': income_summary['dividend_total'],
            'Interest': income_summary['interest_total'],
            'CD Interest': income_summary['cd_interest_total'],
            'Tax': income_summary['tax_total'],
            'Net Total': (
                income_summary['net_total'] +
                trading_summary['net_total']
            )
        }
        self.writers['profit_loss_csv'].output([summary_record])

    def _prepare_log_content(self, 
                           income_summary: Dict, 
                           trading_summary: Dict, 
                           total_summary: Dict) -> str:
        """ログ内容の準備"""
        lines = ["Investment Summary Report"]
        lines.append("-" * 30)
        
        lines.append("\nIncome Summary:")
        lines.append(f"Dividend Total: ${income_summary['dividend_total']:.2f}")
        lines.append(f"Interest Total: ${income_summary['interest_total']:.2f}")
        if income_summary['cd_interest_total']:
            lines.append(f"CD Interest Total: ${income_summary['cd_interest_total']:.2f}")
        lines.append(f"Tax Total: ${income_summary['tax_total']:.2f}")
        lines.append(f"Net Income: ${income_summary['net_total']:.2f}")
        
        lines.append("\nTrading Summary:")
        lines.append(f"Stock Trading Gain: ${trading_summary['stock_gain']:.2f}")
        lines.append(f"Option Trading Gain: ${trading_summary['option_gain']:.2f}")
        lines.append(f"Option Premium Income: ${trading_summary['premium_income']:.2f}")
        lines.append(f"Net Trading Gain: ${trading_summary['net_total']:.2f}")
        
        lines.append("\nTotal Summary:")
        lines.append(f"Total Income: ${total_summary['total_income']:.2f}")
        lines.append(f"Total Trading: ${total_summary['total_trading']:.2f}")
        lines.append(f"Grand Total: ${total_summary['grand_total']:.2f}")
        
        return "\n".join(lines)

    def cleanup(self) -> None:
        """コンテキストのクリーンアップ"""
        # キャッシュのクリア
        if hasattr(self.exchange_rate_provider, 'clear_cache'):
            self.exchange_rate_provider.clear_cache()
        
        # 結果のクリア
        self.processing_results = None
        
        self.logger.info("Application context cleaned up")