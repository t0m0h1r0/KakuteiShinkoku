from enum import Enum
from typing import List, Dict
from decimal import Decimal

class Currency(Enum):
    """通貨を表現する列挙型"""
    USD = ('USD', '$', 2)  # (コード, シンボル, 小数点以下桁数)
    JPY = ('JPY', '¥', 0)
    EUR = ('EUR', '€', 2)
    GBP = ('GBP', '£', 2)
    
    def __init__(self, code: str, symbol: str, decimals: int):
        self._code = code
        self._symbol = symbol
        self._decimals = decimals

    @property
    def code(self) -> str:
        return self._code

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def decimals(self) -> int:
        return self._decimals

    def get_decimal_factor(self) -> Decimal:
        """通貨の小数点以下桁数に基づく係数を取得"""
        return Decimal(f"0.{'0' * self._decimals}")

    @classmethod
    def supported_currencies(cls) -> List['Currency']:
        """サポートされる通貨のリストを取得"""
        return list(cls)

    @classmethod
    def get_currency_pairs(cls) -> List[tuple['Currency', 'Currency']]:
        """有効な通貨ペアの組み合わせを取得"""
        currencies = cls.supported_currencies()
        return [(c1, c2) for c1 in currencies for c2 in currencies if c1 != c2]
    
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

    def __str__(self) -> str:
        """通貨のシンボルを返す"""
        return self._symbol