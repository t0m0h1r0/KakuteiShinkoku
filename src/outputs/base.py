from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, Union
from decimal import Decimal

from ..exchange.money import Money
from ..exchange.currency import Currency

class BaseFormatter(ABC):
    """出力フォーマット基底クラス"""
    
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'GREEN': '\033[92m',
        'WARNING': '\033[93m',
        'RED': '\033[91m',
        'END': '\033[0m',
        'BOLD': '\033[1m'
    }

    def __init__(self, use_color: bool = False):
        self.use_color = use_color

    @abstractmethod
    def format(self, data: Any) -> str:
        """データをフォーマット"""
        pass

    def format_money(self, value: Union[Money, Decimal], currency: str = 'USD') -> str:
        """金額のフォーマット"""
        if isinstance(value, Money):
            amount = value.usd if currency == 'USD' else value.jpy
        else:
            amount = Decimal(str(value))

        is_jpy = currency == 'JPY'
        formatted = self._format_number(amount, is_jpy)
        
        if amount < 0:
            formatted = f"-{formatted}"
            if self.use_color:
                return f"{self.COLORS['RED']}{formatted}{self.COLORS['END']}"
                
        return formatted

    def _format_number(self, amount: Decimal, is_jpy: bool = False) -> str:
        """数値のフォーマット処理"""
        if is_jpy:
            return f"¥{int(abs(amount)):,}"
        
        whole, decimal = f"{abs(amount):.2f}".split('.')
        return f"${int(whole):,}.{decimal}"

    def _color(self, text: str, color: str) -> str:
        """色付き文字列の生成"""
        if not self.use_color:
            return text
        return f"{self.COLORS[color]}{text}{self.COLORS['END']}"

class BaseOutput(ABC):
    """出力処理の基底クラス"""
    
    def __init__(self, formatter: Optional[BaseFormatter] = None):
        self.formatter = formatter
        
    @abstractmethod
    def output(self, data: Any) -> None:
        """データを出力"""
        pass

    def _format_data(self, data: Any) -> str:
        """データのフォーマット処理"""
        if self.formatter is None:
            return str(data)
        return self.formatter.format(data)

    def set_formatter(self, formatter: BaseFormatter) -> None:
        """フォーマッターの設定"""
        self.formatter = formatter