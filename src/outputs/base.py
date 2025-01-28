from abc import ABC, abstractmethod
from typing import Optional, TypeVar, Generic, Union
from decimal import Decimal
from dataclasses import dataclass

from ..exchange.money import Money

T = TypeVar('T')

@dataclass
class ColorScheme:
    """色スキーマのデータクラス定義"""
    HEADER: str = '\033[95m'
    BLUE: str = '\033[94m'
    GREEN: str = '\033[92m'
    WARNING: str = '\033[93m'
    RED: str = '\033[91m'
    END: str = '\033[0m'
    BOLD: str = '\033[1m'

class BaseFormatter(ABC, Generic[T]):
    """
    出力フォーマットの抽象基本クラス

    このクラスは、異なる出力先（コンソール、ファイルなど）に
    データをフォーマットするための基本的な機能を提供します。
    """

    def __init__(self, use_color: bool = True):
        """
        フォーマッターを初期化

        Args:
            use_color: カラー出力を使用するかどうか
        """
        self.use_color = use_color
        self.color_scheme = ColorScheme() if use_color else None

    @abstractmethod
    def format(self, data: T) -> str:
        """
        データをフォーマット

        Args:
            data: フォーマットするデータ

        Returns:
            フォーマットされた文字列
        """
        pass

    def format_money(self, 
                     value: Union[Money, Decimal], 
                     currency: str = 'USD',
                     use_color: bool = False) -> str:
        """
        金額をフォーマット

        Args:
            value: フォーマットする金額
            currency: 通貨（'USD' または 'JPY'）
            use_color: カラー出力を使用するかどうか

        Returns:
            フォーマットされた金額文字列
        """
        if isinstance(value, Money):
            amount = value.usd if currency == 'USD' else value.jpy
        else:
            amount = Decimal(str(value))

        formatted = self._format_number(amount, currency == 'JPY')
        
        if amount < 0 and use_color and self.use_color and self.color_scheme:
            return f"{self.color_scheme.RED}{formatted}{self.color_scheme.END}"
        
        return formatted

    def _format_number(self, amount: Decimal, is_jpy: bool = False) -> str:
        """
        数値をフォーマット

        Args:
            amount: フォーマットする数値
            is_jpy: 日本円の場合True

        Returns:
            フォーマットされた文字列
        """
        if is_jpy:
            return f"¥{int(abs(amount)):,}"
        
        whole, decimal = f"{abs(amount):.2f}".split('.')
        return f"${int(whole):,}.{decimal}"

    def _color(self, text: str, color: str) -> str:
        """
        色付きテキストを生成

        Args:
            text: カラーリングするテキスト
            color: 色の名前

        Returns:
            カラーリングされたテキスト
        """
        if not self.use_color or not self.color_scheme:
            return text
        
        color_code = getattr(self.color_scheme, color.upper(), '')
        return f"{color_code}{text}{self.color_scheme.END}" if color_code else text

class BaseOutput(ABC, Generic[T]):
    """
    出力処理の抽象基本クラス

    異なる出力先に対する共通の出力インターフェースを提供します。
    """

    def __init__(self, formatter: Optional[BaseFormatter[T]] = None):
        """
        出力クラスを初期化

        Args:
            formatter: オプションのフォーマッター
        """
        self.formatter = formatter

    @abstractmethod
    def output(self, data: T) -> None:
        """
        データを出力

        Args:
            data: 出力するデータ
        """
        pass

    def format_data(self, data: T) -> str:
        """
        データをフォーマット

        Args:
            data: フォーマットするデータ

        Returns:
            フォーマットされた文字列
        """
        return str(data) if self.formatter is None else self.formatter.format(data)

    # 下位互換性のためのエイリアス
    def _format_data(self, data: T) -> str:
        """
        下位互換性のためのformat_dataのエイリアス

        将来的には削除する予定
        """
        return self.format_data(data)

    def set_formatter(self, formatter: BaseFormatter[T]) -> None:
        """
        フォーマッターを設定

        Args:
            formatter: 設定するフォーマッター
        """
        self.formatter = formatter