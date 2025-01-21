import csv
import logging
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from typing import Dict

from ..config.settings import (
    FILE_ENCODING, 
    DEFAULT_EXCHANGE_RATE, 
    EXCHANGE_RATE_FILE
)

class RateProviderError(Exception):
    """為替レートプロバイダーのエラー"""
    pass

class RateProvider:
    """為替レートプロバイダー"""
    
    def __init__(self, rate_file: Path = EXCHANGE_RATE_FILE):
        """
        為替レートプロバイダーを初期化
        
        Args:
            rate_file (Path): 為替レートファイルのパス
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self._rate_file = rate_file
        self._rates: Dict[date, Decimal] = {}
        
        # レートの読み込み
        self._load_rates()

    def _load_rates(self) -> None:
        """
        為替レートファイルを読み込む
        
        Raises:
            RateProviderError: レートの読み込みに失敗した場合
        """
        try:
            with self._rate_file.open('r', encoding=FILE_ENCODING) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rate_date = self._parse_date(row['Date'].strip())
                        rate = Decimal(row[' Close'].strip())
                        self._rates[rate_date] = rate
                    except (ValueError, KeyError) as e:
                        self.logger.warning(f"レートデータの解析エラー: {e}")
                        continue
            
            if not self._rates:
                raise RateProviderError("為替レートが見つかりませんでした")
        
        except FileNotFoundError:
            self.logger.warning(f"為替レートファイルが見つかりません: {self._rate_file}")
            # デフォルトレートを使用
            self._rates = {}

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """
        日付文字列をパース
        
        Args:
            date_str (str): 日付文字列
        
        Returns:
            date: パースされた日付
        
        Raises:
            ValueError: 日付のパースに失敗した場合
        """
        date_formats = ['%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y']
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        raise ValueError(f"サポートされていない日付形式: {date_str}")

    def get_rate(self, target_date: date) -> Decimal:
        """
        指定された日付の為替レートを取得
        
        Args:
            target_date (date): 為替レートを取得したい日付
        
        Returns:
            Decimal: 為替レート、見つからない場合はデフォルト値
        """
        # レートが空の場合、デフォルトレートを返す
        if not self._rates:
            self.logger.warning(f"為替レートが見つかりません。デフォルトレート {DEFAULT_EXCHANGE_RATE} を使用します。")
            return DEFAULT_EXCHANGE_RATE

        # 完全一致するレートがある場合
        if target_date in self._rates:
            return self._rates[target_date]

        # 最も近い日付のレートを検索
        closest_date = min(
            self._rates.keys(), 
            key=lambda d: abs((d - target_date).days)
        )
        
        # 30日以内の最近の日付のレートを返す
        if abs((closest_date - target_date).days) <= 30:
            return self._rates[closest_date]

        # それでも見つからない場合はデフォルトレートを返す
        self.logger.warning(
            f"{target_date}の為替レートが見つかりません。"
            f"最も近い日付 {closest_date} のレート、または "
            f"デフォルトレート {DEFAULT_EXCHANGE_RATE} を使用します。"
        )
        return DEFAULT_EXCHANGE_RATE