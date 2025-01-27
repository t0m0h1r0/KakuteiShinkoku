"""
アプリケーション設定管理モジュール

このモジュールは、アプリケーションの設定を管理します。
設定のロード、バリデーション、アクセスなどの機能を提供します。
"""

from pathlib import Path
import logging
import logging.config
from decimal import Decimal
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ..core.error import ConfigurationError

@dataclass
class ExchangeRateConfig:
    """為替レート設定

    Attributes:
        base: 基準通貨
        target: 対象通貨
        default_rate: デフォルトレート
        history_file: 履歴ファイルパス
    """
    base: str
    target: str
    default_rate: Decimal
    history_file: Optional[Path] = None

@dataclass
class LoggingConfig:
    """ロギング設定

    Attributes:
        console_level: コンソールログレベル
        file_level: ファイルログレベル
        log_dir: ログディレクトリ
        log_file: ログファイル名
        log_format: ログフォーマット
    """
    console_level: str
    file_level: str
    log_dir: Path
    log_file: str
    log_format: str

@dataclass
class OutputConfig:
    """出力設定

    Attributes:
        dividend_history: 配当履歴出力パス
        dividend_summary: 配当サマリー出力パス
        interest_history: 利子履歴出力パス
        stock_trade_history: 株式取引履歴出力パス
        option_trade_history: オプション取引履歴出力パス
        option_summary: オプションサマリー出力パス
        final_summary: 最終サマリー出力パス
    """
    dividend_history: Path
    dividend_summary: Path
    interest_history: Path
    stock_trade_history: Path
    option_trade_history: Path
    option_summary: Path
    final_summary: Path

class ApplicationConfig:
    """アプリケーション設定クラス
    
    設定ファイルの読み込み、バリデーション、アクセスを管理します。
    
    Attributes:
        config_data: 生の設定データ
        exchange_config: 為替設定
        logging_config: ロギング設定
        output_config: 出力設定
        debug: デバッグモード
        use_color: カラー出力設定
    """

    def __init__(self, config_data: Dict[str, Any]):
        """初期化
        
        Args:
            config_data: 設定データ辞書
            
        Raises:
            ConfigurationError: 設定が無効な場合
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config_data = config_data
        
        try:
            self._validate_config()
            self._initialize_config()
        except Exception as e:
            raise ConfigurationError(f"設定の初期化に失敗: {e}")

    def _validate_config(self) -> None:
        """設定の検証
        
        Raises:
            ConfigurationError: 必須設定が不足している場合
        """
        required_keys = {
            'exchange', 'logging', 'output_files', 
            'debug', 'use_color'
        }
        
        missing_keys = required_keys - set(self.config_data.keys())
        if missing_keys:
            raise ConfigurationError(
                f"必須設定が不足しています: {missing_keys}"
            )

    def _initialize_config(self) -> None:
        """設定の初期化"""
        self._initialize_exchange_config()
        self._initialize_logging_config()
        self._initialize_output_config()

    def _initialize_exchange_config(self) -> None:
        """為替設定の初期化"""
        exchange_data = self.config_data['exchange']
        self.exchange_config = []
        
        for pair in exchange_data.get('pairs', []):
            self.exchange_config.append(ExchangeRateConfig(
                base=pair['base'],
                target=pair['target'],
                default_rate=Decimal(str(pair['default_rate'])),
                history_file=Path(pair['history_file']) 
                    if 'history_file' in pair else None
            ))

    def _initialize_logging_config(self) -> None:
        """ロギング設定の初期化"""
        log_data = self.config_data['logging']
        self.logging_config = LoggingConfig(
            console_level=log_data['console_level'],
            file_level=log_data['file_level'],
            log_dir=Path(log_data['log_dir']),
            log_file=log_data['log_file'],
            log_format=log_data['log_format']
        )

    def _initialize_output_config(self) -> None:
        """出力設定の初期化"""
        output_data = self.config_data['output_files']
        self.output_config = OutputConfig(
            dividend_history=Path(output_data['dividend_history']),
            dividend_summary=Path(output_data['dividend_summary']),
            interest_history=Path(output_data['interest_history']),
            stock_trade_history=Path(output_data['stock_trade_history']),
            option_trade_history=Path(output_data['option_trade_history']),
            option_summary=Path(output_data['option_summary']),
            final_summary=Path(output_data['final_summary'])
        )

    def get_transaction_files(self) -> List[Path]:
        """取引ファイルパスの取得
        
        Returns:
            取引ファイルパスのリスト
        """
        patterns = self.config_data.get('transaction_files', [])
        return [Path(pattern) for pattern in patterns]

    def get_output_paths(self) -> Dict[str, Path]:
        """出力パスの取得
        
        Returns:
            出力パスの辞書
        """
        return {
            'dividend_history': self.output_config.dividend_history,
            'dividend_summary': self.output_config.dividend_summary,
            'interest_history': self.output_config.interest_history,
            'stock_trade_history': self.output_config.stock_trade_history,
            'option_trade_history': self.output_config.option_trade_history,
            'option_summary': self.output_config.option_summary,
            'final_summary': self.output_config.final_summary
        }

    def create_logging_config(self) -> Dict[str, Any]:
        """ロギング設定の作成
        
        Returns:
            ロギング設定辞書
        """
        log_dir = self.logging_config.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

        return {
            'version': 1,
            'formatters': {
                'detailed': {
                    'format': self.logging_config.log_format
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'formatter': 'detailed',
                    'level': self.logging_config.console_level
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': str(log_dir / self.logging_config.log_file),
                    'formatter': 'detailed',
                    'level': self.logging_config.file_level
                }
            },
            'root': {
                'handlers': ['console', 'file'],
                'level': self.logging_config.file_level
            }
        }

    def ensure_output_directories(self) -> None:
        """出力ディレクトリの作成
        
        全ての出力ディレクトリが存在することを確認し、
        必要に応じて作成します。
        """
        for path in self.get_output_paths().values():
            path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def debug(self) -> bool:
        """デバッグモード設定の取得"""
        return self.config_data.get('debug', False)

    @property
    def use_color(self) -> bool:
        """カラー出力設定の取得"""
        return self.config_data.get('use_color', True)

    def validate_paths(self) -> List[str]:
        """パスの検証
        
        Returns:
            エラーメッセージのリスト
        """
        errors = []
        
        # 取引ファイルの検証
        for tx_file in self.get_transaction_files():
            if not tx_file.exists():
                errors.append(f"取引ファイルが見つかりません: {tx_file}")

        # 為替レート履歴ファイルの検証
        for rate_config in self.exchange_config:
            if rate_config.history_file and not rate_config.history_file.exists():
                errors.append(
                    f"為替レート履歴ファイルが見つかりません: {rate_config.history_file}"
                )

        return errors