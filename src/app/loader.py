from pathlib import Path
from typing import Dict, Any
import logging

from ..formatters.text_formatter import TextFormatter
from ..outputs.csv import CSVOutput

class ComponentLoader:
    """コンポーネント初期化を担当するクラス"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_csv_writers(self, text_formatter: TextFormatter) -> Dict[str, CSVOutput]:
        """CSVライターの作成"""
        paths = self.config.get_output_paths()
        return {
            'dividend_csv': self._create_dividend_writer(paths['dividend_history']),
            'interest_csv': self._create_interest_writer(paths['interest_history']),
            'stock_trade_csv': self._create_stock_writer(paths['stock_trade_history']),
            'option_trade_csv': self._create_option_writer(paths['option_trade_history']),
            'option_summary_csv': self._create_option_summary_writer(paths['option_summary']),
            'final_summary_csv': self._create_summary_writer(paths['final_summary'])
        }

    def _create_dividend_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'gross_amount', 'tax_amount', 'net_amount',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
            'exchange_rate'
        ])

    def _create_interest_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'gross_amount', 'tax_amount', 'net_amount',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
            'exchange_rate'
        ])

    def _create_stock_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'quantity', 'price', 'realized_gain',
            'price_jpy', 'realized_gain_jpy',
            'exchange_rate'
        ])

    def _create_option_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'quantity', 'option_type', 'strike_price',
            'expiry_date', 'underlying',
            'price', 'fees', 
            'trading_pnl', 'premium_pnl',
            'price_jpy', 'fees_jpy', 
            'trading_pnl_jpy', 'premium_pnl_jpy',
            'exchange_rate', 'position_type', 
            'is_closed', 'is_expired', 'is_assigned'
        ])

    def _create_option_summary_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'account', 'symbol', 'description', 'underlying',
            'option_type', 'strike_price', 'expiry_date',
            'open_date', 'close_date', 'status',
            'initial_quantity', 'remaining_quantity',
            'trading_pnl', 'premium_pnl', 'total_fees',
            'trading_pnl_jpy', 'premium_pnl_jpy', 'total_fees_jpy',
            'exchange_rate'
        ])

    def _create_summary_writer(self, path: Path) -> CSVOutput:
        return CSVOutput(path, [
            'category', 'subcategory',
            'gross_amount_usd', 'tax_amount_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy'
        ])