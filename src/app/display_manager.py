from typing import Dict
from ..config.settings import LOG_DIR, OUTPUT_FILES
from ..formatters.text_formatter import TextFormatter
from ..outputs.console_output import ConsoleOutput, ColorConsoleOutput
from ..outputs.logfile_output import LogFileOutput

class DisplayManager:
    """表示出力の管理クラス"""
    
    @staticmethod
    def create_outputs(use_color: bool = True) -> Dict:
        """表示出力の設定"""
        text_formatter = TextFormatter()
        
        return {
            'console': ColorConsoleOutput(text_formatter) if use_color else ConsoleOutput(text_formatter),
            'log_file': LogFileOutput(
                output_path=LOG_DIR / 'processing_summary.log',
                formatter=text_formatter,
                line_prefix='[SUMMARY] '
            )
        }