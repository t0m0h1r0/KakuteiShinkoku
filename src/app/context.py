# app/context.py

import logging
import logging.config
from pathlib import Path
from typing import Dict, Any, Optional, cast

from ..core.loader import JSONLoader
from ..outputs.console import ConsoleOutput
from ..outputs.file import LogFileOutput
from ..outputs.csv import CSVOutput
from ..processors.dividend.processor import DividendProcessor
from ..processors.interest.processor import InterestProcessor
from ..processors.stock.processor import StockProcessor
from ..processors.option.processor import OptionProcessor
from .loader import ComponentLoader


class ApplicationContext:
    """
    アプリケーションのコンテキストを管理するクラス

    このクラスは以下の責務を持ちます：
    - 各種コンポーネントの初期化と管理
    - 処理結果の保持
    - リソースの適切なクリーンアップ
    """

    def __init__(self, config: Any, use_color_output: bool = True) -> None:
        """
        コンテキストを初期化

        Args:
            config: アプリケーション設定
            use_color_output: カラー出力を使用するかどうか
        """
        self.config = config
        self.use_color = use_color_output
        self.component_loader = ComponentLoader(config)
        self.logger = logging.getLogger(self.__class__.__name__)

        try:
            self.logger.debug("アプリケーション設定を開始...")
            self._initialize_core_components()
            self._initialize_processors()
            self._initialize_outputs()
            self.logger.info("コンテキストの初期化が完了しました")

        except Exception as e:
            self.logger.error(f"コンテキスト初期化中にエラー: {e}")
            raise

    def _initialize_core_components(self) -> None:
        """コアコンポーネントの初期化"""
        self.logger.debug("コアコンポーネントの初期化...")
        self.transaction_loader = JSONLoader()
        self.processing_results: Optional[Dict[str, Any]] = None

    def _initialize_processors(self) -> None:
        """データプロセッサの初期化"""
        self.logger.debug("データプロセッサの初期化...")

        try:
            self.dividend_processor = DividendProcessor()
            self.interest_processor = InterestProcessor()
            self.stock_processor = StockProcessor()
            self.option_processor = OptionProcessor()
        except Exception as e:
            self.logger.error(f"プロセッサの初期化中にエラー: {e}")
            raise

    def _initialize_outputs(self) -> None:
        """出力コンポーネントの初期化"""
        self.logger.debug("出力コンポーネントの初期化...")

        try:
            self.display_outputs = self._create_display_outputs()
            self.writers = self._create_writers()
        except Exception as e:
            self.logger.error(f"出力コンポーネントの初期化中にエラー: {e}")
            raise

    def _create_display_outputs(self) -> Dict[str, Any]:
        """表示出力の作成"""
        log_dir = Path(self.config.logging_config["log_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)

        return {
            "console": ConsoleOutput(self.use_color),
            "log_file": LogFileOutput(
                output_path=log_dir / "processing_summary.log", line_prefix="[SUMMARY] "
            ),
        }

    def _create_writers(self) -> Dict[str, Any]:
        """ライターの作成"""
        writers = self.component_loader.create_csv_writers()
        writers["console"] = cast(CSVOutput, self.display_outputs["console"])
        return writers

    def cleanup(self) -> None:
        """リソースのクリーンアップ"""
        self.logger.debug("コンテキストのクリーンアップを開始...")

        try:
            # 将来的なクリーンアップ処理をここに追加
            pass
        except Exception as e:
            self.logger.error(f"クリーンアップ中にエラー: {e}")
        finally:
            self.logger.info("クリーンアップが完了しました")
