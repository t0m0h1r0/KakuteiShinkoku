from typing import Dict
from ..config.settings import LOG_DIR, OUTPUT_FILES
from ..formatters.text_formatter import TextFormatter
from ..outputs.factory import create_output

class DisplayManager:
    """表示出力の管理クラス"""
    
    @staticmethod
    def create_outputs(use_color: bool = True) -> Dict:
        """表示出力の設定"""
        text_formatter = TextFormatter()
        
        return {
            'console': create_output(
                'console',
                use_color=use_color,
                formatter=text_formatter
            ),
            'summary_file': create_output(
                'file',
                output_path=OUTPUT_FILES['profit_loss_summary'],
                formatter=text_formatter
            ),
            'log_file': create_output(
                'log',
                output_path=LOG_DIR / 'processing_summary.log',
                formatter=text_formatter,
                prefix='[SUMMARY] '
            )
        }