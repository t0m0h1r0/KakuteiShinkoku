from enum import Enum
from decimal import Decimal

class Currency(Enum):
    """通貨を表現する列挙型"""
    USD = 'USD'
    JPY = 'JPY'
    
    def __init__(self, code: str):
        self._details = self._get_currency_details()
    
    def _get_currency_details(self) -> dict:
        """通貨の詳細情報を取得"""
        details = {
            'USD': {'code': 'USD', 'symbol': '$', 'decimals': 2},
            'JPY': {'code': 'JPY', 'symbol': '¥', 'decimals': 0}
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

    @classmethod
    def from_str(cls, currency_str: str) -> 'Currency':
        """文字列から通貨を取得"""
        currency_map = {
            'USD': cls.USD, '$': cls.USD,
            'JPY': cls.JPY, '¥': cls.JPY
        }
        normalized = str(currency_str).upper().strip()
        return currency_map.get(normalized)

    def __str__(self) -> str:
        return self.symbol