from enum import Enum, auto
from typing import List

class Currency(Enum):
    """サポートされる通貨の列挙型"""
    USD = auto()
    JPY = auto()
    EUR = auto()
    GBP = auto()
    
    @classmethod
    def supported_currencies(cls) -> List['Currency']:
        """サポートされる通貨のリストを返す"""
        return [cls.USD, cls.JPY, cls.EUR, cls.GBP]
    
    def __str__(self) -> str:
        """通貨のシンボルを返す"""
        return {
            Currency.USD: '$',
            Currency.JPY: '¥',
            Currency.EUR: '€',
            Currency.GBP: '£'
        }[self]
    
    @classmethod
    def from_str(cls, currency_str: str) -> 'Currency':
        """文字列から通貨を取得"""
        currency_map = {
            'USD': cls.USD, '$': cls.USD,
            'JPY': cls.JPY, '¥': cls.JPY,
            'EUR': cls.EUR, '€': cls.EUR,
            'GBP': cls.GBP, '£': cls.GBP
        }
        normalized = currency_str.upper().strip()
        if normalized not in currency_map:
            raise ValueError(f"サポートされていない通貨: {currency_str}")
        return currency_map[normalized]