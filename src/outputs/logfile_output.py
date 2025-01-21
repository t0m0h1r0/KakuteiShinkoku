from pathlib import Path
from typing import Any, Optional

from .base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter

class LogFileOutput(BaseOutput):
    """ログファイル出力クラス"""
    
    def __init__(self, 
                 output_path: Path, 
                 formatter: Optional[BaseFormatter] = None,
                 encoding: str = 'utf-8', 
                 line_prefix: str = ''):
        super().__init__(formatter)
        self.output_path = output_path
        self.encoding = encoding
        self.line_prefix = line_prefix

    def output(self, data: Any) -> None:
        """プレフィックス付きでデータを出力"""
        try:
            # 出力ディレクトリの作成
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # データを文字列に変換
            if not isinstance(data, str):
                if self.formatter is not None:
                    formatted_data = self._format_data(data)
                else:
                    formatted_data = str(data)
            else:
                formatted_data = data
            
            # 各行にプレフィックスを追加
            if self.line_prefix:
                formatted_data = "\n".join(
                    f"{self.line_prefix}{line}" 
                    for line in formatted_data.split("\n")
                )
            
            with self.output_path.open('a', encoding=self.encoding) as f:
                f.write(formatted_data + "\n")
            
            self.logger.info(f"Successfully wrote log to {self.output_path}")
            
        except Exception as e:
            self.logger.error(f"Error writing to log file {self.output_path}: {e}")
            raise