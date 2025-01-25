from pathlib import Path
import logging
import logging.config
from typing import Dict, Any

class ApplicationConfig:
    """アプリケーション設定管理クラス"""

    def __init__(self, config_data: Dict[str, Any]):
        self.config_data = config_data
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_output_paths(self) -> Dict[str, Path]:
        """出力パスの取得"""
        return {key: Path(path) for key, path in self.config_data['output_files'].items()}

    def create_logging_config(self) -> Dict[str, Any]:
        """ロギング設定の作成"""
        log_dir = Path(self.config_data['logging']['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)

        return {
            'version': 1,
            'formatters': {
                'detailed': {
                    'format': self.config_data['logging']['log_format']
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': self.config_data['logging']['console_level']
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': str(log_dir / self.config_data['logging']['log_file']),
                    'formatter': 'detailed',
                    'level': self.config_data['logging']['file_level']
                }
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': self.config_data['logging']['file_level']
            }
        }

    @property
    def debug(self) -> bool:
        """デバッグモードの取得"""
        return self.config_data.get('debug', False)

    @property
    def use_color(self) -> bool:
        """カラー出力設定の取得"""
        return self.config_data.get('use_color', True)

    @property
    def logging_config(self) -> Dict[str, Any]:
        """ロギング設定の取得"""
        return self.config_data['logging']