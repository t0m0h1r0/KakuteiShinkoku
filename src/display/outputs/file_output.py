from pathlib import Path
from typing import Any, Optional
from .base import BaseOutput
from ..formatters.base import BaseFormatter

class FileOutput(BaseOutput):
    """ファイル出力クラス"""
    
    def __init__(self, output_path: Path, formatter: Optional[BaseFormatter] = None,
                 encoding: str = 'utf-8', mode: str = 'w'):
        super().__init__(formatter)
        self.output_path = output_path
        self.encoding = encoding
        self.mode = mode

    def output(self, data: Any) -> None:
        """データをファイルに出力"""
        try:
            # 出力ディレクトリの作成
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # データのフォーマットと出力
            formatted_data = self._format_data(data)
            
            with self.output_path.open(mode=self.mode, encoding=self.encoding) as f:
                f.write(formatted_data)
            
            self.logger.info(f"Successfully wrote data to {self.output_path}")
            
        except Exception as e:
            self.logger.error(f"Error writing to file {self.output_path}: {e}")
            raise

class AppendFileOutput(FileOutput):
    """追記モードのファイル出力クラス"""
    
    def __init__(self, output_path: Path, formatter: Optional[BaseFormatter] = None,
                 encoding: str = 'utf-8'):
        super().__init__(output_path, formatter, encoding, mode='a')

class LogFileOutput(FileOutput):
    """ログファイル出力クラス"""
    
    def __init__(self, output_path: Path, formatter: Optional[BaseFormatter] = None,
                 encoding: str = 'utf-8'):
        super().__init__(output_path, formatter, encoding)
        self.line_prefix = ""
    
    def set_line_prefix(self, prefix: str) -> None:
        """行プレフィックスを設定"""
        self.line_prefix = prefix
    
    def output(self, data: Any) -> None:
        """プレフィックス付きでデータを出力"""
        try:
            formatted_data = self._format_data(data)
            
            # 各行にプレフィックスを追加
            if self.line_prefix:
                formatted_data = "\n".join(
                    f"{self.line_prefix}{line}" 
                    for line in formatted_data.split("\n")
                )
            
            with self.output_path.open(mode=self.mode, encoding=self.encoding) as f:
                f.write(formatted_data + "\n")
            
            self.logger.info(f"Successfully wrote log to {self.output_path}")
            
        except Exception as e:
            self.logger.error(f"Error writing to log file {self.output_path}: {e}")
            raise