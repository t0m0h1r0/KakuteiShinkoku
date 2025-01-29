from pathlib import Path
from typing import Any, Optional
import logging

from .base import BaseOutput, BaseFormatter


class FileFormatter(BaseFormatter):
    """ファイル出力用フォーマッター"""

    def format(self, data: Any) -> str:
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)


class FileOutput(BaseOutput):
    """ファイル出力の基本クラス"""

    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
        mode: str = "w",
        line_prefix: str = "",
    ):
        """
        ファイル出力クラスを初期化

        Args:
            output_path: 出力先パス
            formatter: カスタムフォーマッター（オプション）
            encoding: ファイルエンコーディング
            mode: ファイルオープンモード
            line_prefix: 行プレフィックス
        """
        formatter = formatter or FileFormatter()
        super().__init__(formatter)
        self.output_path = output_path
        self.encoding = encoding
        self.mode = mode
        self.line_prefix = line_prefix
        self.logger = logging.getLogger(self.__class__.__name__)

    def output(self, data: Any) -> None:
        """
        データをファイルに出力

        Args:
            data: 出力するデータ
        """
        try:
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            formatted_data = self._format_data(data)

            if self.line_prefix:
                formatted_data = self._add_line_prefix(formatted_data)

            with self.output_path.open(mode=self.mode, encoding=self.encoding) as f:
                f.write(formatted_data + "\n")

            self.logger.info(f"{self.output_path}への書き込みが完了")

        except Exception as e:
            self.logger.error(f"ファイル出力エラー: {e}")
            raise

    def _add_line_prefix(self, text: str) -> str:
        """
        各行にプレフィックスを追加

        Args:
            text: 元のテキスト

        Returns:
            プレフィックスが追加されたテキスト
        """
        return "\n".join(f"{self.line_prefix}{line}" for line in text.split("\n"))


class AppendFileOutput(FileOutput):
    """追記モードのファイル出力クラス"""

    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
    ):
        """
        追記モードのファイル出力を初期化

        Args:
            output_path: 出力先パス
            formatter: カスタムフォーマッター（オプション）
            encoding: ファイルエンコーディング
        """
        super().__init__(
            output_path=output_path, formatter=formatter, encoding=encoding, mode="a"
        )


class LogFileOutput(FileOutput):
    """ログファイル出力クラス"""

    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
        line_prefix: str = "[LOG] ",
    ):
        """
        ログファイル出力を初期化

        Args:
            output_path: 出力先パス
            formatter: カスタムフォーマッター（オプション）
            encoding: ファイルエンコーディング
            line_prefix: ログのプレフィックス
        """
        super().__init__(
            output_path=output_path,
            formatter=formatter,
            encoding=encoding,
            mode="a",
            line_prefix=line_prefix,
        )
