import sys
import logging
import logging.config
from pathlib import Path
import argparse
from datetime import datetime
from decimal import Decimal
import yaml
from typing import Dict, Any, List, Optional, NoReturn

from .app.context import ApplicationContext
from .app.processor import InvestmentProcessor
from .exchange.exchange import exchange
from .exchange.currency import Currency


class Config:
    """アプリケーション設定を管理するクラス"""

    def __init__(self, config_path: Path) -> None:
        """
        設定を初期化

        Args:
            config_path: 設定ファイルのパス

        Raises:
            FileNotFoundError: 設定ファイルが存在しない場合
            yaml.YAMLError: YAMLの解析に失敗した場合
        """
        self.config = self._load_yaml(config_path)

    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """
        YAMLファイルから設定を読み込む

        Args:
            config_path: 設定ファイルのパス

        Returns:
            Dict[str, Any]: 読み込んだ設定

        Raises:
            FileNotFoundError: 設定ファイルが存在しない場合
            yaml.YAMLError: YAMLの解析に失敗した場合
        """
        if not config_path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"設定ファイルの解析に失敗: {e}")

    def get_json_files(self) -> List[Path]:
        """
        JSONファイルのパスリストを取得

        Returns:
            List[Path]: JSONファイルのパスリスト
        """
        return [Path(pattern) for pattern in self.config.get("transaction_files", [])]

    def get_output_paths(self) -> Dict[str, Path]:
        """
        出力ファイルのパス辞書を取得

        Returns:
            Dict[str, Path]: 出力ファイルのパス辞書
        """
        return {key: Path(path) for key, path in self.config["output_files"].items()}

    def create_logging_config(self) -> Dict[str, Any]:
        """
        ロギング設定を生成

        Returns:
            Dict[str, Any]: ロギング設定辞書
        """
        log_dir = Path(self.config["logging"]["log_dir"])
        log_dir.mkdir(parents=True, exist_ok=True)

        return {
            "version": 1,
            "formatters": {
                "detailed": {"format": self.config["logging"]["log_format"]}
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "detailed",
                    "level": self.config["logging"]["console_level"],
                },
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(log_dir / self.config["logging"]["log_file"]),
                    "formatter": "detailed",
                    "level": self.config["logging"]["file_level"],
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": self.config["logging"]["file_level"],
            },
        }

    @property
    def debug(self) -> bool:
        """デバッグモードフラグ"""
        return self.config.get("debug", False)

    @property
    def use_color(self) -> bool:
        """カラー出力フラグ"""
        return self.config.get("use_color", True)

    @property
    def logging_config(self) -> Dict[str, Any]:
        """ロギング設定"""
        return self.config["logging"]

    @property
    def exchange_config(self) -> Dict[str, Any]:
        """為替設定"""
        return self.config["exchange"]


def initialize_exchange_rates(config: Config) -> None:
    """
    為替レートプロバイダーを初期化

    Args:
        config: アプリケーション設定

    Raises:
        ValueError: レート設定が不正な場合
    """
    for pair_config in config.exchange_config["pairs"]:
        try:
            exchange.add_rate_source(
                Currency.from_str(pair_config["base"]),
                Currency.from_str(pair_config["target"]),
                Decimal(str(pair_config["default_rate"])),
                Path(pair_config["history_file"])
                if "history_file" in pair_config
                else None,
            )
        except (KeyError, ValueError) as e:
            raise ValueError(f"為替レート設定が不正です: {e}")


def parse_arguments() -> argparse.Namespace:
    """
    コマンドライン引数をパース

    Returns:
        argparse.Namespace: パースされた引数

    Raises:
        argparse.ArgumentError: 引数のパースに失敗した場合
    """
    parser = argparse.ArgumentParser(
        description="投資データ処理プログラム",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="設定ファイルのパス",
    )
    return parser.parse_args()


def handle_keyboard_interrupt() -> NoReturn:
    """
    キーボード割り込みの処理

    Returns:
        NoReturn: プログラムを終了
    """
    logging.warning("ユーザーにより処理が中断されました")
    sys.exit(130)


def handle_unexpected_error(e: Exception) -> NoReturn:
    """
    予期せぬエラーの処理

    Args:
        e: 発生した例外

    Returns:
        NoReturn: プログラムを終了
    """
    logging.exception(f"予期せぬエラーが発生しました: {e}")
    sys.exit(1)


def main() -> int:
    """
    メインエントリーポイント

    Returns:
        int: 終了コード
    """
    start_time = datetime.now()
    args = parse_arguments()
    context: Optional[ApplicationContext] = None

    try:
        # 設定の初期化
        config = Config(args.config)
        logging.config.dictConfig(config.create_logging_config())
        logger = logging.getLogger(__name__)

        # アプリケーションコンテキストの作成
        context = ApplicationContext(config, use_color_output=config.use_color)
        logger.info("投資データ処理を開始...")

        # 為替レートプロバイダーの初期化
        initialize_exchange_rates(config)

        # 処理対象ファイルの取得
        json_files = config.get_json_files()
        if not json_files:
            logger.error("処理対象のJSONファイルが見つかりません")
            return 1

        logger.info(f"処理対象ファイル数: {len(json_files)}")

        # データ処理の実行
        processor = InvestmentProcessor(context)
        if not processor.process_files(json_files):
            logger.error("データ処理に失敗しました")
            return 1

        # 処理完了
        execution_time = datetime.now() - start_time
        logger.info(f"処理が完了しました (所要時間: {execution_time})")
        return 0

    except KeyboardInterrupt:
        return handle_keyboard_interrupt()
    except Exception as e:
        return handle_unexpected_error(e)
    finally:
        if context:
            context.cleanup()


if __name__ == "__main__":
    sys.exit(main())