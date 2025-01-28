from pathlib import Path
from typing import Any, Optional
import logging

from .base import BaseOutput, BaseFormatter


class FileFormatter(BaseFormatter):
    def format(self, data: Any) -> str:
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)


class FileOutput(BaseOutput):
    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
        mode: str = "w",
        line_prefix: str = "",
    ):
        formatter = formatter or FileFormatter()
        super().__init__(formatter)
        self.output_path = output_path
        self.encoding = encoding
        self.mode = mode
        self.line_prefix = line_prefix
        self.logger = logging.getLogger(self.__class__.__name__)

    def output(self, data: Any) -> None:
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
        return "\n".join(f"{self.line_prefix}{line}" for line in text.split("\n"))


class AppendFileOutput(FileOutput):
    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
    ):
        super().__init__(
            output_path=output_path, formatter=formatter, encoding=encoding, mode="a"
        )


class LogFileOutput(FileOutput):
    def __init__(
        self,
        output_path: Path,
        formatter: Optional[BaseFormatter] = None,
        encoding: str = "utf-8",
        line_prefix: str = "[LOG] ",
    ):
        super().__init__(
            output_path=output_path,
            formatter=formatter,
            encoding=encoding,
            mode="a",
            line_prefix=line_prefix,
        )
