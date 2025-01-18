from pathlib import Path
import logging.config

from src.config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, OUTPUT_FILES,
    LOGGING_CONFIG
)
from src.utils.exchange_rates import ExchangeRateProvider, ExchangeRateCache
from src.processors.transaction_loader import JSONTransactionLoader
from src.processors.dividend import DividendProcessor
from src.processors.trade import TradeProcessor
from src.writers.csv_writer import CSVWriter
from src.writers.console_writer import ConsoleWriter

class ApplicationContext:
    """アプリケーションのコンテキスト管理クラス"""
    
    def __init__(self):
        # ディレクトリとログの設定
        self._setup_directories()
        self._setup_logging()
        
        # ロガーの初期化
        self.logger = logging.getLogger(__name__)
        
        # コンポーネントの初期化
        self.exchange_rate_provider = self._create_exchange_rate_provider()
        self.transaction_loader = JSONTransactionLoader()
        
        # プロセッサーの初期化
        self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
        self.trade_processor = TradeProcessor(self.exchange_rate_provider)
        
        # ライターの初期化
        self.writers = self._setup_writers()

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

    def _create_exchange_rate_provider(self):
        """為替レートプロバイダーの作成"""
        provider = ExchangeRateProvider(EXCHANGE_RATE_FILE)
        return ExchangeRateCache(provider)

    def _setup_writers(self):
        """ライターの設定"""
        return {
            'dividend_csv': CSVWriter(
                OUTPUT_FILES['dividend_history'], 
                fieldnames=[
                    'date', 'account', 'symbol', 'description', 
                    'type', 'gross_amount', 'tax_amount', 'net_amount'
                ]
            ),
            'trade_csv': CSVWriter(
                OUTPUT_FILES['trade_history'], 
                fieldnames=[
                    'date', 'account', 'symbol', 'description', 
                    'type', 'action', 'quantity', 'price'
                ]
            ),
            'console': ConsoleWriter()
        }
