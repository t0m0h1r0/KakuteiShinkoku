# exchange/provider.py

from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
import csv
import logging

from .currency import Currency
from .rate import Rate

class RateSource:
    """為替レートのソースを管理するクラス"""
    def __init__(self, base: Currency, target: Currency, default_rate: Decimal, history_file: Optional[Path] = None):
        self.base = base
        self.target = target
        self.default_rate = default_rate
        self.history_file = history_file
        self.rates: List[Rate] = []
        self.logger = logging.getLogger(self.__class__.__name__)
        
        if history_file:
            self._load_rates()

    def _load_rates(self) -> None:
        """CSVファイルから為替レートを読み込む"""
        if not self.history_file or not self.history_file.exists():
            return

        try:
            with open(self.history_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(line.replace(' ', '') for line in csvfile)
                for row in reader:
                    try:
                        # 日付のパースを修正
                        rate_date = datetime.strptime(row['Date'], '%m/%d/%y').date()
                        rate_value = Decimal(row['Close'])
                        rate = Rate(
                            base=self.base,
                            target=self.target,
                            value=rate_value,
                            date=rate_date
                        )
                        self.rates.append(rate)
                    except Exception as e:
                        self.logger.warning(f"レート解析エラー: {row.get('Date', '不明な日付')} - {e}")

                self.rates.sort(key=lambda x: x.date)
        except Exception as e:
            self.logger.error(f"ファイルからのレート読み込みエラー: {self.history_file} - {e}")

class RateManager:
    """為替レートの管理と取得を行うクラス"""
    def __init__(self):
        self._sources: Dict[tuple[Currency, Currency], RateSource] = {}
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_source(self, source: RateSource) -> None:
        """為替レートのソースを追加"""
        self._sources[(source.base, source.target)] = source

    def get_rate(self, base: Currency, target: Currency, rate_date: date) -> Rate:
        """指定された通貨と日付の為替レートを取得"""
        # 同一通貨の場合は1
        if base == target:
            return Rate(base, target, Decimal('1'), rate_date)

        # 直接のレートを探す
        direct_source = self._sources.get((base, target))
        if direct_source:
            return self._find_rate_for_date(direct_source, rate_date)

        # 逆レートを探す
        inverse_source = self._sources.get((target, base))
        if inverse_source:
            rate = self._find_rate_for_date(inverse_source, rate_date)
            return rate.inverse()

        # クロスレートを試みる
        cross_rate = self._calculate_cross_rate(base, target, rate_date)
        if cross_rate:
            return cross_rate

        # デフォルトレートを返す
        return self._create_default_rate(base, target, rate_date)

    def _find_rate_for_date(self, source: RateSource, rate_date: date) -> Rate:
        """指定された日付に最も近いレートを取得"""
        matching_rates = [rate for rate in source.rates if rate.date <= rate_date]
        
        if matching_rates:
            return max(matching_rates, key=lambda r: r.date)

        # マッチするレートがない場合はデフォルトレート
        return Rate(
            base=source.base,
            target=source.target,
            value=source.default_rate,
            date=rate_date
        )

    def _calculate_cross_rate(self, base: Currency, target: Currency, rate_date: date) -> Optional[Rate]:
        """USDを介したクロスレートを計算"""
        usd_base_source = self._sources.get((Currency.USD, base))
        usd_target_source = self._sources.get((Currency.USD, target))

        if usd_base_source and usd_target_source:
            base_rate = self._find_rate_for_date(usd_base_source, rate_date)
            target_rate = self._find_rate_for_date(usd_target_source, rate_date)
            
            return Rate(
                base=base,
                target=target,
                value=target_rate.value / base_rate.value,
                date=max(base_rate.date, target_rate.date)
            )
        
        return None

    def _create_default_rate(self, base: Currency, target: Currency, rate_date: date) -> Rate:
        """デフォルトのレートを作成"""
        return Rate(
            base=base,
            target=target,
            value=Decimal('1.0'),
            date=rate_date
        )

    def clear(self) -> None:
        """すべてのレートソースをクリア"""
        self._sources.clear()