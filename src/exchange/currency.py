from enum import Enum
from decimal import Decimal
from typing import List, Dict, Optional, Union

class Currency(Enum):
    """通貨を表現する列挙型"""
    USD = 'USD'
    JPY = 'JPY'
    EUR = 'EUR'
    GBP = 'GBP'
    
    def __init__(self, code: str):
        self._details = self._get_currency_details()
    
    def _get_currency_details(self) -> Dict[str, Union[str, int]]:
        """通貨の詳細情報を取得"""
        details = {
            'USD': {'code': 'USD', 'symbol': '$', 'decimals': 2},
            'JPY': {'code': 'JPY', 'symbol': '¥', 'decimals': 0},
            'EUR': {'code': 'EUR', 'symbol': '€', 'decimals': 2},
            'GBP': {'code': 'GBP', 'symbol': '£', 'decimals': 2}
        }
        return details[self.value]

    @property
    def code(self) -> str:
        """通貨コードを取得"""
        return self._details['code']

    @property
    def symbol(self) -> str:
        """通貨シンボルを取得"""
        return self._details['symbol']

    @property
    def decimals(self) -> int:
        """小数点以下桁数を取得"""
        return self._details['decimals']

    def get_decimal_factor(self) -> Decimal:
        """通貨の小数点以下桁数に基づく係数を取得"""
        return Decimal(f"0.{'0' * self.decimals}")

    @classmethod
    def supported_currencies(cls) -> List['Currency']:
        """サポートされる通貨のリストを取得"""
        return list(cls)

    @classmethod
    def get_currency_pairs(cls) -> List[tuple['Currency', 'Currency']]:
        """有効な通貨ペアの組み合わせを取得"""
        return [(c1, c2) for c1 in cls.supported_currencies() for c2 in cls.supported_currencies() if c1 != c2]

    @classmethod
    def from_str(cls, currency_str: str) -> Optional['Currency']:
        """文字列から通貨を取得
        
        Args:
            currency_str (str): 通貨文字列（コードまたはシンボル）
        
        Returns:
            Optional[Currency]: 対応する通貨。見つからない場合はNone
        """
        currency_map = {
            'USD': cls.USD, '$': cls.USD,
            'JPY': cls.JPY, '¥': cls.JPY,
            'EUR': cls.EUR, '€': cls.EUR,
            'GBP': cls.GBP, '£': cls.GBP
        }
        
        normalized = str(currency_str).upper().strip()
        return currency_map.get(normalized)

    def __str__(self) -> str:
        """通貨のシンボルを返す"""
        return self.symbol