import os
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
import yaml
import logging
from dataclasses import dataclass, field
from functools import cached_property

class ConfigurationError(Exception):
    """設定関連の例外"""
    pass

@dataclass
class ConfigOptions:
    """設定オプションのデフォルト値と検証を管理"""
    debug: bool = False
    use_color: bool = True
    
    # トランザクションファイル設定
    transaction_files: List[str] = field(default_factory=list)
    
    # 為替レート設定
    exchange_rate_default: float = 150.0
    
    # ロギング設定
    logging_config: Dict[str, str] = field(default_factory=lambda: {
        'console_level': 'ERROR',
        'file_level': 'DEBUG',
        'log_dir': 'output/logs',
        'log_file': 'processing.log',
        'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    })
    
    # 出力ファイル設定
    output_files: Dict[str, str] = field(default_factory=lambda: {
        'dividend_history': 'output/dividend_history.csv',
        'dividend_summary': 'output/dividend_summary.csv',
        'interest_history': 'output/interest_history.csv',
        'stock_trade_history': 'output/stock_history.csv',
        'option_trade_history': 'output/option_history.csv',
        'option_summary': 'output/option_summary.csv',
        'final_summary': 'output/final_summary.csv'
    })

class ConfigManager:
    """高度な設定管理クラス"""
    
    def __init__(
        self, 
        config_path: Optional[Union[str, Path]] = None, 
        env_prefix: str = 'INVESTMENT_'
    ):
        """
        設定マネージャを初期化
        
        Args:
            config_path: 設定ファイルのパス
            env_prefix: 環境変数の接頭辞
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.env_prefix = env_prefix
        
        # デフォルトの設定
        self._config_options = ConfigOptions()
        
        # 設定ファイルのロード
        if config_path:
            self._load_config_file(config_path)
        
        # 環境変数での上書き
        self._override_from_env()
        
        # 設定の検証
        self._validate_config()

    def _load_config_file(self, config_path: Union[str, Path]) -> None:
        """
        設定ファイルから設定をロード
        
        Args:
            config_path: 設定ファイルのパス
        """
        try:
            path = Path(config_path)
            if not path.exists():
                self.logger.warning(f"設定ファイルが見つかりません: {path}")
                return
            
            with path.open('r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
                self._merge_config(file_config)
        
        except Exception as e:
            self.logger.error(f"設定ファイルの読み込み中にエラー: {e}")
            raise ConfigurationError(f"設定ファイルの読み込みに失敗: {e}")

    def _merge_config(self, file_config: Dict[str, Any]) -> None:
        """
        ファイルからの設定とデフォルト設定をマージ
        
        Args:
            file_config: ファイルから読み込んだ設定
        """
        # デバッグと色設定
        if 'debug' in file_config:
            self._config_options.debug = bool(file_config['debug'])
        if 'use_color' in file_config:
            self._config_options.use_color = bool(file_config['use_color'])
        
        # トランザクションファイル
        if 'transaction_files' in file_config:
            self._config_options.transaction_files = file_config['transaction_files']
        
        # 為替レート
        if 'default_exchange_rate' in file_config:
            self._config_options.exchange_rate_default = float(file_config['default_exchange_rate'])
        
        # ロギング設定
        if 'logging' in file_config:
            logging_config = file_config['logging']
            self._config_options.logging_config.update({
                k: v for k, v in logging_config.items() 
                if k in self._config_options.logging_config
            })
        
        # 出力ファイル設定
        if 'output_files' in file_config:
            self._config_options.output_files.update({
                k: v for k, v in file_config['output_files'].items() 
                if k in self._config_options.output_files
            })

    def _override_from_env(self) -> None:
        """
        環境変数による設定の上書き
        """
        try:
            # デバッグモード
            debug_env = os.getenv(f'{self.env_prefix}DEBUG')
            if debug_env is not None:
                self._config_options.debug = debug_env.lower() in ['true', '1', 'yes']
            
            # カラー出力
            color_env = os.getenv(f'{self.env_prefix}USE_COLOR')
            if color_env is not None:
                self._config_options.use_color = color_env.lower() in ['true', '1', 'yes']
            
            # トランザクションファイル
            transaction_files_env = os.getenv(f'{self.env_prefix}TRANSACTION_FILES')
            if transaction_files_env:
                self._config_options.transaction_files = transaction_files_env.split(',')
            
            # 為替レート
            exchange_rate_env = os.getenv(f'{self.env_prefix}EXCHANGE_RATE')
            if exchange_rate_env:
                try:
                    self._config_options.exchange_rate_default = float(exchange_rate_env)
                except ValueError:
                    self.logger.warning("無効な為替レートの環境変数")
        
        except Exception as e:
            self.logger.error(f"環境変数からの設定上書き中にエラー: {e}")

    def _validate_config(self) -> None:
        """
        設定の検証
        """
        # トランザクションファイルの存在確認
        for file_path in self._config_options.transaction_files:
            if not Path(file_path).exists():
                self.logger.warning(f"トランザクションファイルが見つかりません: {file_path}")
        
        # 出力ディレクトリの作成
        for output_path in self._config_options.output_files.values():
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # ログディレクトリの作成
        Path(self._config_options.logging_config['log_dir']).mkdir(parents=True, exist_ok=True)

    @property
    def debug(self) -> bool:
        """デバッグモードのプロパティ"""
        return self._config_options.debug

    @property
    def use_color(self) -> bool:
        """カラー出力のプロパティ"""
        return self._config_options.use_color

    @property
    def transaction_files(self) -> List[str]:
        """トランザクションファイルのリスト"""
        return self._config_options.transaction_files

    @property
    def default_exchange_rate(self) -> float:
        """デフォルトの為替レート"""
        return self._config_options.exchange_rate_default

    @cached_property
    def logging_config(self) -> Dict[str, str]:
        """ロギング設定"""
        return dict(self._config_options.logging_config)

    @cached_property
    def output_files(self) -> Dict[str, str]:
        """出力ファイルのパス"""
        return dict(self._config_options.output_files)

    def create_logging_config(self) -> Dict[str, Any]:
        """
        ロギング設定を生成
        
        Returns:
            ロギング設定の辞書
        """
        return {
            'version': 1,
            'formatters': {
                'detailed': {
                    'format': self.logging_config['log_format']
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': self.logging_config['console_level']
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': str(Path(self.logging_config['log_dir']) / self.logging_config['log_file']),
                    'formatter': 'detailed',
                    'level': self.logging_config['file_level']
                }
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': self.logging_config['file_level']
            }
        }