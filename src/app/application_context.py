import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal

from ..core.transaction_loader import JSONTransactionLoader
from ..processors.dividend_processor import DividendProcessor
from ..processors.interest_processor import InterestProcessor
from ..processors.stock_processor import StockProcessor
from ..processors.option_processor import OptionProcessor
from ..outputs.console_output import ConsoleOutput, ColorConsoleOutput
from ..outputs.logfile_output import LogFileOutput
from ..outputs.csv_writer import CSVWriter
from ..formatters.text_formatter import TextFormatter

class ApplicationContext:
    """アプリケーションのコンテキストを管理するクラス"""
    
    def __init__(self, config, use_color_output: bool = True):
        """
        ApplicationContextの初期化
        
        Args:
            config: アプリケーション設定
            use_color_output: カラー出力を使用するかどうか
        """
        self.config = config
        self._setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        try:
            self.logger.debug("アプリケーション設定を開始...")
            self._initialize_components()
            self.logger.info("アプリケーションコンテキストの初期化が完了しました")
            
        except Exception as e:
            self.logger.error(f"コンテキスト初期化中にエラーが発生: {e}")
            raise

    def _initialize_components(self) -> None:
        """コンポーネントの初期化"""
        self._initialize_core_components()
        self._initialize_processors()
        self._initialize_outputs()
        
    def _initialize_core_components(self) -> None:
        """コアコンポーネントの初期化"""
        self.transaction_loader = JSONTransactionLoader()
        self.processing_results: Optional[Dict[str, Any]] = None

    def _initialize_processors(self) -> None:
        """各種プロセッサの初期化"""
        self.logger.debug("プロセッサの初期化を開始...")
        
        self.dividend_processor = DividendProcessor()
        self.interest_processor = InterestProcessor()
        self.stock_processor = StockProcessor()
        self.option_processor = OptionProcessor()

    def _initialize_outputs(self) -> None:
        """出力コンポーネントの初期化"""
        self.logger.debug("出力コンポーネントの初期化を開始...")
        
        text_formatter = TextFormatter()
        self.display_outputs = self._create_display_outputs(text_formatter)
        self.writers = self._create_writers()

    def _create_display_outputs(self, formatter: TextFormatter) -> Dict:
        """表示出力の作成"""
        summary_log = self._get_summary_log_path()
        summary_log.parent.mkdir(parents=True, exist_ok=True)
        
        return {
            'console': ColorConsoleOutput(formatter) if self.config.use_color else ConsoleOutput(formatter),
            'log_file': LogFileOutput(
                output_path=summary_log,
                formatter=formatter,
                line_prefix='[SUMMARY] '
            )
        }

    def _create_writers(self) -> Dict:
        """CSVライターの作成"""
        paths = self.config.get_output_paths()
        
        writers = {
            'console': self.display_outputs['console'],
            'dividend_csv': self._create_dividend_writer(paths),
            'interest_csv': self._create_interest_writer(paths),
            'stock_trade_csv': self._create_stock_trade_writer(paths),
            'option_trade_csv': self._create_option_trade_writer(paths),
            'option_summary_csv': self._create_option_summary_writer(paths),
            'final_summary_csv': self._create_final_summary_writer(paths)
        }
        
        return writers

    def _get_summary_log_path(self) -> Path:
        """サマリーログのパスを取得"""
        return self.config.logging_config['log_dir'] / 'processing_summary.log'

    def _create_dividend_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """配当CSVライターの作成"""
        return CSVWriter(
            paths['dividend_history'],
            fieldnames=[
                'date', 'account', 'symbol', 'description',
                'action', 'gross_amount', 'tax_amount', 'net_amount',
                'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
                'exchange_rate'
            ]
        )

    def _create_interest_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """利子CSVライターの作成"""
        return CSVWriter(
            paths['interest_history'],
            fieldnames=[
                'date', 'account', 'symbol', 'description',
                'action', 'gross_amount', 'tax_amount', 'net_amount',
                'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
                'exchange_rate'
            ]
        )

    def _create_stock_trade_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """株式取引CSVライターの作成"""
        return CSVWriter(
            paths['stock_trade_history'],
            fieldnames=[
                'date', 'account', 'symbol', 'description',
                'action', 'quantity', 'price', 'realized_gain',
                'price_jpy', 'realized_gain_jpy',
                'exchange_rate'
            ]
        )

    def _create_option_trade_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """オプション取引CSVライターの作成"""
        return CSVWriter(
            paths['option_trade_history'],
            fieldnames=[
                'date', 'account', 'symbol', 'description',
                'action', 'quantity', 'option_type', 'strike_price',
                'expiry_date', 'underlying',
                'price', 'fees', 
                'trading_pnl', 'premium_pnl',
                'price_jpy', 'fees_jpy', 
                'trading_pnl_jpy', 'premium_pnl_jpy',
                'exchange_rate', 'position_type', 
                'is_closed', 'is_expired', 'is_assigned'
            ]
        )

    def _create_option_summary_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """オプションサマリーCSVライターの作成"""
        return CSVWriter(
            paths['option_summary'],
            fieldnames=[
                'account', 'symbol', 'description', 'underlying',
                'option_type', 'strike_price', 'expiry_date',
                'open_date', 'close_date', 'status',
                'initial_quantity', 'remaining_quantity',
                'trading_pnl', 'premium_pnl', 'total_fees',
                'trading_pnl_jpy', 'premium_pnl_jpy', 'total_fees_jpy',
                'exchange_rate'
            ]
        )

    def _create_final_summary_writer(self, paths: Dict[str, Path]) -> CSVWriter:
        """最終サマリーCSVライターの作成"""
        return CSVWriter(
            paths['final_summary'],
            fieldnames=[
                'category', 'subcategory',
                'gross_amount_usd', 'tax_amount_usd', 'net_amount_usd',
                'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy'
            ]
        )

    def _setup_logging(self) -> None:
        """ロギングの設定"""
        log_config = self._create_logging_config()
        logging.config.dictConfig(log_config)

    def _create_logging_config(self) -> Dict[str, Any]:
        """ロギング設定の作成"""
        log_dir = Path(self.config.logging_config['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)

        return {
            'version': 1,
            'formatters': {
                'detailed': {
                    'format': self.config.logging_config['log_format']
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': self.config.logging_config['console_level']
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': str(log_dir / self.config.logging_config['log_file']),
                    'formatter': 'detailed',
                    'level': self.config.logging_config['file_level']
                }
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': self.config.logging_config['file_level']
            }
        }

    def cleanup(self) -> None:
        """コンテキストのクリーンアップ"""
        self.logger.debug("コンテキストのクリーンアップを開始...")
        self.logger.info("コンテキストのクリーンアップが完了しました")