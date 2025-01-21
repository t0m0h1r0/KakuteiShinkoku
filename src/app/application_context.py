import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional, List
from decimal import Decimal

from ..config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, LOGGING_CONFIG, OUTPUT_FILES
)
from ..exchange.rate_provider import RateProvider
from ..core.transaction_loader import JSONTransactionLoader
from ..processors.dividend_processor import DividendProcessor
from ..processors.interest_income import InterestProcessor
from ..processors.stock_trade import StockTradeProcessor
from ..processors.option_processor import OptionProcessor

from .display_manager import DisplayManager
from .writer_manager import WriterManager
from .cleanup_handler import CleanupHandler

class ApplicationContext:
    """アプリケーションのコンテキスト管理クラス"""
    
    def __init__(self, use_color_output: bool = True):
        # ログ設定の初期化
        self._setup_logging()
        
        # ロガーの初期化
        self.logger = logging.getLogger(self.__class__.__name__)
        
        try:
            # ディレクトリの設定
            self.logger.debug("Setting up directories...")
            self._setup_directories()
            
            # 為替レートプロバイダーの初期化
            self.logger.debug("Initializing exchange rate provider...")
            self.exchange_rate_provider = RateProvider()
            
            # トランザクションローダーの初期化
            self.logger.debug("Initializing transaction loader...")
            self.transaction_loader = JSONTransactionLoader()
            
            # 各種プロセッサーを初期化
            self.logger.debug("Initializing processors...")
            self._initialize_processors()
            
            # 出力系の初期化
            self.logger.debug("Initializing output systems...")
            self.display_outputs = DisplayManager.create_outputs(use_color_output)
            
            # ライターの初期化（出力先を設定）
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
            config = LOGGING_CONFIG.copy()
            config['handlers']['file']['filename'] = str(LOG_DIR / 'processing.log')
            
            logging.config.dictConfig(config)
        except Exception as e:
            print(f"Error setting up logging: {e}")
            raise

    def _setup_directories(self):
        """ディレクトリ構造の設定"""
        for directory in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
            self.logger.debug(f"Creating directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)
        
        # 出力ディレクトリの作成
        for output_path in OUTPUT_FILES.values():
            output_path.parent.mkdir(parents=True, exist_ok=True)

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