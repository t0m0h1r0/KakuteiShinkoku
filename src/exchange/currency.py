# exchange/currency.py

from enum import Enum, unique
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, ClassVar, Dict, Union, overload

@dataclass(frozen=True)
class CurrencyInfo:
    """通貨の詳細情報を表すイミュータブルなデータクラス"""
    code: str
    symbol: str
    decimals: int
    display_name: str
    country: Optional[str] = None

@unique
class Currency(Enum):
    """通貨を表現する列挙型"""
    USD = CurrencyInfo('USD', '$', 2, 'US Dollar', 'United States')
    JPY = CurrencyInfo('JPY', '¥', 0, 'Japanese Yen', 'Japan')
    EUR = CurrencyInfo('EUR', '€', 2, 'Euro', 'European Union')
    GBP = CurrencyInfo('GBP', '£', 2, 'British Pound', 'United Kingdom')
    CHF = CurrencyInfo('CHF', 'CHF', 2, 'Swiss Franc', 'Switzerland')
    CAD = CurrencyInfo('CAD', 'C$', 2, 'Canadian Dollar', 'Canada')
    AUD = CurrencyInfo('AUD', 'A$', 2, 'Australian Dollar', 'Australia')

    def __init__(self, info: CurrencyInfo):
        """通貨情報の初期化"""
        object.__setattr__(self, '_info', info)

    @property
    def code(self) -> str:
        """通貨コードを取得"""
        return self._info.code

    @property
    def symbol(self) -> str:
        """通貨シンボルを取得"""
        return self._info.symbol

    @property
    def decimals(self) -> int:
        """小数点以下の桁数を取得"""
        return self._info.decimals

    @property
    def display_name(self) -> str:
        """表示名を取得"""
        return self._info.display_name

    @property
    def country(self) -> Optional[str]:
        """国名を取得"""
        return self._info.country

    def format_amount(
        self, 
        amount: Union[Decimal, float, int], 
        include_symbol: bool = True
    ) -> str:
        """
        金額を通貨形式でフォーマット
        
        Args:
            amount: フォーマットする金額
            include_symbol: シンボルを含めるかどうか
        
        Returns:
            フォーマットされた金額文字列
        """
        try:
            # Decimalに変換
            decimal_amount = Decimal(str(amount))
            
            # 金額のフォーマット
            if self.decimals == 0:
                formatted = f"{int(decimal_amount):,}"
            else:
                formatted = f"{decimal_amount:,.{self.decimals}f}"
            
            # シンボルの追加
            return f"{self.symbol}{formatted}" if include_symbol else formatted
        
        except (TypeError, ValueError) as e:
            # エラーハンドリング
            raise ValueError(f"金額のフォーマットに失敗: {amount}") from e

    @classmethod
    @overload
    def from_str(cls, value: str) -> Optional['Currency']:
        """文字列から通貨を取得（コード優先）"""
        ...

    @classmethod
    def from_str(
        cls, 
        value: Optional[str], 
        default: Optional['Currency'] = None
    ) -> Optional['Currency']:
        """
        文字列から通貨を取得
        
        Args:
            value: 通貨を特定する文字列
            default: デフォルトで返す通貨（見つからない場合）
        
        Returns:
            対応する通貨。見つからない場合はdefaultまたはNone
        """
        if not value:
            return default
        
        # 大文字に変換して比較
        upper_value = value.upper().strip()
        
        # コードで検索
        try:
            return cls(cls._member_map_[upper_value])
        except KeyError:
            pass
        
        # シンボルで検索
        for currency in cls:
            if currency.symbol == value:
                return currency
        
        return default

    def __str__(self) -> str:
        """通貨コードを文字列として返す"""
        return self.code

    def __repr__(self) -> str:
        """開発者向けの文字列表現"""
        return f"Currency.{self.name}"

    @classmethod
    def get_supported_currencies(cls) -> Dict[str, 'Currency']:
        """
        サポートされている通貨の辞書を返す
        
        Returns:
            通貨コードをキーとする通貨の辞書
        """
        return {currency.code: currency for currency in cls}