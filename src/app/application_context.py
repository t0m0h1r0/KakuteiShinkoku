import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional
from decimal import Decimal

from ..config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, LOGGING_CONFIG
)
from ..exchange.factories import create_rate_provider
from ..processors.transaction_loader import JSONTransactionLoader
from ..processors.dividend_income import DividendProcessor
from ..processors.interest_income import InterestProcessor
from ..processors.stock_trade import StockTradeProcessor
from ..processors.option_trade import OptionTradeProcessor
from ..processors.option_premium import OptionPremiumProcessor

from .display_manager import DisplayManager
from .writer_manager import WriterManager
from .cleanup_handler import CleanupHandler

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
        
        # トランザクションローダーの初期化
        self.transaction_loader = JSONTransactionLoader()
        
        # 各種プロセッサーを初期化
        self._initialize_processors()
        
        # 出力系の初期化
        self.display_outputs = DisplayManager.create_outputs(use_color_output)
        self.writers = WriterManager.create_writers(self.display_outputs)
        
        # 処理結果の保存用
        self.processing_results: Optional[Dict[str, Any]] = None

    def _setup_logging(self):
        """ログ設定"""
        logging.config.dictConfig(LOGGING_CONFIG)

    def _setup_directories(self):
        """ディレクトリ構造の設定"""
        for directory in [DATA_DIR, OUTPUT_DIR, LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        if not EXCHANGE_RATE_FILE.exists():
            raise FileNotFoundError(f"Exchange rate file not found: {EXCHANGE_RATE_FILE}")

    def _initialize_processors(self):
        """各種プロセッサーの初期化"""
        self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
        self.interest_processor = InterestProcessor(self.exchange_rate_provider)
        self.stock_processor = StockTradeProcessor(self.exchange_rate_provider)
        self.option_processor = OptionTradeProcessor(self.exchange_rate_provider)
        self.premium_processor = OptionPremiumProcessor(self.exchange_rate_provider)

    def cleanup(self) -> None:
        """コンテキストのクリーンアップ"""
        CleanupHandler.cleanup_context(self)