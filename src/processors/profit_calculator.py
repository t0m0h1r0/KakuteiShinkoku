from typing import Dict, List, Any
from decimal import Decimal
from collections import defaultdict
import logging
import re

from ..core.types.money import Money
from .context import ApplicationContext

class ProfitLossCalculator:
    """損益計算クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_summary(self, dividend_records: List, trade_records: List) -> Dict:
        """詳細な損益サマリーを計算"""
        try:
            # シンボルと種別ごとの集計用辞書
            summary_dict = self._initialize_summary_dict()

            # 配当・利子収入の集計
            self._calculate_dividend_summary(summary_dict, dividend_records)

            # 取引損益の集計
            self._calculate_trade_summary(summary_dict, trade_records)

            # 結果の整形
            return self._format_summary_results(summary_dict)

        except Exception as e:
            self.logger.error(f"Profit/Loss calculation error: {e}", exc_info=True)
            raise

    def _initialize_summary_dict(self) -> Dict:
        """集計用辞書の初期化"""
        return defaultdict(lambda: {
            'Gain or Loss (USD)': Decimal('0'),
            'Tax (USD)': Decimal('0'),
            'Rate(USDJPY)': Decimal('0'),
            'Gain or Loss (JPY)': Decimal('0'),
            'Tax (JPY)': Decimal('0'),
            'Count': 0
        })

    def _calculate_dividend_summary(self, summary_dict: Dict, dividend_records: List) -> None:
        """配当・利子収入の集計"""
        for record in dividend_records:
            key = (record.symbol or 'Unknown', record.income_type)
            summary = summary_dict[key]
            
            summary['Gain or Loss (USD)'] += record.gross_amount.amount
            summary['Tax (USD)'] += record.tax_amount.amount
            summary['Rate(USDJPY)'] = record.exchange_rate
            summary['Gain or Loss (JPY)'] += record.gross_amount.amount * record.exchange_rate
            summary['Tax (JPY)'] += record.tax_amount.amount * record.exchange_rate
            summary['Count'] += 1

    def _calculate_trade_summary(self, summary_dict: Dict, trade_records: List) -> None:
        """取引損益の集計"""
        for record in trade_records:
            if hasattr(record, 'realized_gain'):
                key = self._determine_trade_key(record)
                summary = summary_dict[key]
                
                summary['Gain or Loss (USD)'] += record.realized_gain.amount
                summary['Rate(USDJPY)'] = record.exchange_rate
                summary['Gain or Loss (JPY)'] += record.realized_gain.amount * record.exchange_rate
                summary['Count'] += 1

    def _determine_trade_key(self, record) -> tuple:
        """取引のキーを決定"""
        if record.trade_type == 'Option':
            symbol = self._extract_option_base_symbol(record.symbol)
            return (symbol, 'Option')
        return (record.symbol or 'Unknown', record.trade_type)

    @staticmethod
    def _extract_option_base_symbol(symbol: str) -> str:
        """オプションシンボルから基本シンボルを抽出"""
        try:
            match = re.match(r'^(\w+)', symbol)
            return match.group(1) if match else symbol
        except Exception:
            return symbol

    def _format_summary_results(self, summary_dict: Dict) -> List[Dict]:
        """集計結果のフォーマット"""
        formatted_results = []
        
        for (symbol, type_), amounts in summary_dict.items():
            if amounts['Count'] > 0:
                formatted_results.append({
                    'Symbol': symbol,
                    'Type': type_,
                    'Gain or Loss (USD)': f"{amounts['Gain or Loss (USD)']:.2f}",
                    'Tax (USD)': f"{amounts['Tax (USD)']:.2f}",
                    'Rate(USDJPY)': f"{amounts['Rate(USDJPY)']:.2f}",
                    'Gain or Loss (JPY)': f"{amounts['Gain or Loss (JPY)']:.2f}",
                    'Tax (JPY)': f"{amounts['Tax (JPY)']:.2f}",
                    'Count': amounts['Count']
                })

        return formatted_results