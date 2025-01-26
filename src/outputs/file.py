from pathlib import Path
from typing import Any, Optional, Union
from .base import BaseOutput, BaseFormatter

class FileOutput(BaseOutput):
   """ファイル出力の基本クラス"""
   
   def __init__(self, 
                output_path: Path,
                formatter: Optional[BaseFormatter] = None,
                encoding: str = 'utf-8', 
                mode: str = 'w',
                line_prefix: str = ''):
       super().__init__(formatter)
       self.output_path = output_path
       self.encoding = encoding
       self.mode = mode
       self.line_prefix = line_prefix

   def output(self, data: Any) -> None:
       """データをファイルに出力"""
       try:
           # 出力ディレクトリの作成
           self.output_path.parent.mkdir(parents=True, exist_ok=True)
           
           # データのフォーマット
           formatted_data = self._format_data(data)
           if self.line_prefix:
               formatted_data = self._add_line_prefix(formatted_data)
           
           # ファイルへの書き込み
           with self.output_path.open(mode=self.mode, encoding=self.encoding) as f:
               f.write(formatted_data + "\n")
           
           self.logger.info(f"{self.output_path}への書き込みが完了")
           
       except Exception as e:
           self.logger.error(f"ファイル出力エラー: {e}")
           raise

   def _add_line_prefix(self, text: str) -> str:
       """各行にプレフィックスを追加"""
       return "\n".join(
           f"{self.line_prefix}{line}" 
           for line in text.split("\n")
       )

class AppendFileOutput(FileOutput):
   """追記モードのファイル出力"""
   
   def __init__(self, output_path: Path, 
                formatter: Optional[BaseFormatter] = None,
                encoding: str = 'utf-8'):
       super().__init__(
           output_path=output_path, 
           formatter=formatter,
           encoding=encoding,
           mode='a'
       )

class LogFileOutput(FileOutput):
   """ログファイル出力"""
   
   def __init__(self, output_path: Path,
                formatter: Optional[BaseFormatter] = None,
                encoding: str = 'utf-8',
                line_prefix: str = '[LOG] '):
       super().__init__(
           output_path=output_path,
           formatter=formatter,
           encoding=encoding,
           mode='a',
           line_prefix=line_prefix
       )