import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional

from ..core.transaction_loader import JSONTransactionLoader
from ..outputs.console import ConsoleOutput
from ..outputs.file import LogFileOutput
from ..formatters.text_formatter import TextFormatter
from ..processors.dividend.processor import DividendProcessor
from ..processors.interest.processor import InterestProcessor
from ..processors.stock.processor import StockProcessor
from ..processors.option.processor import OptionProcessor
from .loader import ComponentLoader

class ApplicationContext:
    def __init__(self, config, use_color_output: bool = True):
        self.config = config
        self.use_color = use_color_output
        self.component_loader = ComponentLoader(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        try:
            self.logger.debug("アプリケーション設定を開始...")
            self._initialize_core()
            self._initialize_processors() 
            self._initialize_outputs()
            self.logger.info("コンテキストの初期化が完了")
            
        except Exception as e:
            self.logger.error(f"コンテキスト初期化中にエラー: {e}")
            raise

    def _initialize_core(self) -> None:
        self.transaction_loader = JSONTransactionLoader()
        self.processing_results: Optional[Dict[str, Any]] = None

    def _initialize_processors(self) -> None:
        self.logger.debug("プロセッサの初期化を開始...")
        self.dividend_processor = DividendProcessor()
        self.interest_processor = InterestProcessor()
        self.stock_processor = StockProcessor()
        self.option_processor = OptionProcessor()

    def _initialize_outputs(self) -> None:
        self.logger.debug("出力コンポーネントの初期化を開始...")
        text_formatter = TextFormatter()
        self.display_outputs = self._create_display_outputs(text_formatter)
        self.writers = self.component_loader.create_csv_writers(text_formatter)
        self.writers['console'] = self.display_outputs['console']

    def _create_display_outputs(self, formatter: TextFormatter) -> Dict:
        log_dir = Path(self.config.logging_config['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            'console': ConsoleOutput(self.use_color),
            'log_file': LogFileOutput(
                output_path=log_dir / 'processing_summary.log',
                formatter=formatter,
                line_prefix='[SUMMARY] '
            )
        }

    def cleanup(self) -> None:
        self.logger.debug("コンテキストのクリーンアップを開始...")
        self.logger.info("クリーンアップが完了")