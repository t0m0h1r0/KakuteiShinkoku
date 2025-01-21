import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional, List
from decimal import Decimal

from ..config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, LOGGING_CONFIG
)
from ..exchange.factories import create_rate_provider
from ..core.transaction_loader import JSONTransactionLoader
from ..processors.dividend_income import DividendProcessor
from ..processors.interest_income import InterestProcessor
from ..processors.stock_trade import StockTradeProcessor
from ..processors.option_processor import OptionProcessor
from ..processors.option_records import OptionTradeRecord, OptionSummaryRecord

from .display_manager import DisplayManager
from .writer_manager import WriterManager
from .cleanup_handler import CleanupHandler

class ApplicationContext:
    """アプリケーションのコンテキスト管理クラス"""
    
    def __init__(self, use_color_output: bool = True):
        # ロガーの初期化（先に実行）
        self._setup_logging()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        try:
            # ディレクトリの設定
            self.logger.debug("Setting up directories...")
            self._setup_directories()
            
            # 為替レートプロバイダーの初期化
            self.logger.debug("Initializing exchange rate provider...")
            self.exchange_rate_provider = create_rate_provider(EXCHANGE_RATE_FILE, use_cache=True)
            
            # トランザクションローダーの初期化
            self.logger.debug("Initializing transaction loader...")
            self.transaction_loader = JSONTransactionLoader()
            
            # 各種プロセッサーを初期化
            self.logger.debug("Initializing processors...")
            self._initialize_processors()
            
            # 出力系の初期化
            self.logger.debug("Initializing output systems...")
            self.display_outputs = DisplayManager.create_outputs(use_color_output)
            self.writers = WriterManager.create_writers(self.display_outputs)
            
            # 処理結果の保存用
            self.processing_results: Optional[Dict[str, Any]] = None
            
            self.logger.info("Application context initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing application context: {e}")
            raise

    def _setup_logging(self):
        """ログ設定"""
        try:
            # ログディレクトリの作成
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            
            # ファイルハンドラーのパスを更新
            LOGGING_CONFIG['handlers']['file']['filename'] = str(LOG_DIR / 'processing.log')
            
            logging.config.dictConfig(LOGGING_CONFIG)
        except Exception as e:
            print(f"Error setting up logging: {e}")
            raise

    def _setup_directories(self):
        """ディレクトリ構造の設定"""
        for directory in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
            self.logger.debug(f"Creating directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
        
        if not EXCHANGE_RATE_FILE.exists():
            self.logger.error(f"Exchange rate file not found: {EXCHANGE_RATE_FILE}")
            raise FileNotFoundError(f"Exchange rate file not found: {EXCHANGE_RATE_FILE}")

    def _initialize_processors(self):
        """各種プロセッサーの初期化"""
        try:
            self.logger.debug("Initializing dividend processor...")
            self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
            
            self.logger.debug("Initializing interest processor...")
            self.interest_processor = InterestProcessor(self.exchange_rate_provider)
            
            self.logger.debug("Initializing stock processor...")
            self.stock_processor = StockTradeProcessor(self.exchange_rate_provider)
            
            self.logger.debug("Initializing option processor...")
            self.option_processor = OptionProcessor(self.exchange_rate_provider)
            
        except Exception as e:
            self.logger.error(f"Error initializing processors: {e}")
            raise
        
    def cleanup(self) -> None:
        """コンテキストのクリーンアップ"""
        try:
            self.logger.debug("Starting context cleanup...")
            CleanupHandler.cleanup_context(self)
            self.logger.info("Context cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            raise

    def display_results(self) -> None:
        """処理結果の表示"""
        if not self.processing_results:
            self.logger.warning("No processing results to display")
            return
            
        try:
            self.logger.debug("Displaying processing results...")

            # オプション取引記録の処理
            self.logger.debug("Processing option trade records...")
            option_records = self.option_processor.get_records()
            formatted_records = self._format_option_record(option_records)
            self.writers['option_trade_csv'].output(formatted_records)
            
            # オプションサマリー記録の処理
            self.logger.debug("Processing option summary records...")
            summary_records = self.option_processor.get_summary_records()
            formatted_summaries = self._format_option_summary(summary_records)
            self.writers['option_summary_csv'].output(formatted_summaries)

        except Exception as e:
            self.logger.error(f"Error displaying results: {e}")
            raise

    def _format_option_record(self, records: List[OptionTradeRecord]) -> List[Dict]:
        """オプション取引記録のフォーマット"""
        return [
            {
                'date': record.trade_date.strftime('%Y-%m-%d'),
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'action': record.action,
                'quantity': record.quantity,
                'option_type': record.option_type,
                'strike_price': float(record.strike_price),
                'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
                'underlying': record.underlying,
                'price': float(record.price.amount),
                'fees': float(record.fees.amount),
                'trading_pnl': float(record.trading_pnl.amount),
                'premium_pnl': float(record.premium_pnl.amount),
                'price_jpy': int(record.price_jpy.amount),
                'fees_jpy': int(record.fees_jpy.amount),
                'trading_pnl_jpy': int(record.trading_pnl_jpy.amount),
                'premium_pnl_jpy': int(record.premium_pnl_jpy.amount),
                'exchange_rate': float(record.exchange_rate),
                'position_type': record.position_type,
                'is_closed': record.is_closed,
                'is_expired': record.is_expired
            }
            for record in records
        ]

    def _format_option_summary(self, records: List[OptionSummaryRecord]) -> List[Dict]:
        """オプション取引サマリー記録のフォーマット"""
        return [
            {
                'account': record.account_id,
                'symbol': record.symbol,
                'description': record.description,
                'underlying': record.underlying,
                'option_type': record.option_type,
                'strike_price': float(record.strike_price),
                'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
                'open_date': record.open_date.strftime('%Y-%m-%d'),
                'close_date': record.close_date.strftime('%Y-%m-%d') if record.close_date else '',
                'status': record.status,
                'initial_quantity': int(record.initial_quantity),
                'remaining_quantity': int(record.remaining_quantity),
                'trading_pnl': float(record.trading_pnl.amount),
                'premium_pnl': float(record.premium_pnl.amount),
                'total_fees': float(record.total_fees.amount),
                'trading_pnl_jpy': int(record.trading_pnl_jpy.amount),
                'premium_pnl_jpy': int(record.premium_pnl_jpy.amount),
                'total_fees_jpy': int(record.total_fees_jpy.amount),
                'exchange_rate': float(record.exchange_rate)
            }
            for record in records
        ]