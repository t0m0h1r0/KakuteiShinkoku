from typing import Dict, Any
from decimal import Decimal

from .base import BaseFormatter, BaseOutput
from ..exchange.money import Money
from ..exchange.currency import Currency

class ConsoleFormatter(BaseFormatter):
    """コンソール出力用フォーマッター"""
    
    def format(self, data: Any) -> str:
        if isinstance(data, dict) and self._is_summary_data(data):
            return self._format_summary(data)
        return str(data)

    def _is_summary_data(self, data: Dict) -> bool:
        return all(key in data for key in ['income', 'trading', 'total'])

    def _format_summary(self, data: Dict) -> str:
        income = data['income']
        trading = data['trading']
        total = data['total']
        
        sections = []
        
        # ヘッダー
        sections.append("投資サマリーレポート")
        sections.append("-" * 40)
        
        # 収入セクション
        header = self._color("収入サマリー:", 'BLUE')
        sections.extend([
            f"\n{header}",
            f"配当総額: {self.format_money(income['dividend_total'])}",
            f"利子総額: {self.format_money(income['interest_total'])}",
            f"税金合計: {self.format_money(income['tax_total'])}",
            f"純収入: {self.format_money(income['net_total'])}"
        ])
        
        # 取引セクション
        header = self._color("取引サマリー:", 'GREEN')
        sections.extend([
            f"\n{header}",
            f"株式取引損益: {self.format_money(trading['stock_gain'])}",
            f"オプション取引損益: {self.format_money(trading['option_gain'])}",
            f"オプションプレミアム収入: {self.format_money(trading['premium_income'])}",
            f"純取引損益: {self.format_money(trading['net_total'])}"
        ])
        
        # 総合計セクション
        header = self._color("総合計:", 'BOLD')
        sections.extend([
            f"\n{header}",
            f"総収入: {self.format_money(total['total_income'])}",
            f"総取引損益: {self.format_money(total['total_trading'])}",
            f"最終合計: {self.format_money(total['grand_total'])}"
        ])
        
        return "\n".join(sections)

class ConsoleOutput(BaseOutput):
    """コンソール出力クラス"""
    
    def __init__(self, use_color: bool = False):
        formatter = ConsoleFormatter(use_color)
        super().__init__(formatter)

    def output(self, data: Any) -> None:
        formatted_data = self._format_data(data)
        print(formatted_data)