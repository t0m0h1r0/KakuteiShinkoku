from pathlib import Path
from typing import Dict, Any
import logging

from ..outputs.csv import CSVOutput

class ComponentLoader:
    """
    アプリケーションコンポーネントのローダー
    
    各種出力コンポーネントの作成と初期化を担当します。
    CSVファイル出力のためのライターを管理します。
    """
    
    def __init__(self, config: Any) -> None:
        """
        ローダーを初期化
        
        Args:
            config: アプリケーション設定
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)

    def create_csv_writers(self) -> Dict[str, CSVOutput]:
        """
        CSVライターを作成
        
        Returns:
            作成されたCSVライターの辞書
            キーは出力タイプ、値はCSVOutputインスタンス
        """
        try:
            self.logger.debug("CSVライターの作成を開始...")
            paths = self.config.get_output_paths()
            
            writers = {
                'dividend_csv': self._create_dividend_writer(paths['dividend_history']),
                'interest_csv': self._create_interest_writer(paths['interest_history']),
                'stock_trade_csv': self._create_stock_writer(paths['stock_trade_history']),
                'option_trade_csv': self._create_option_writer(paths['option_trade_history']),
                'option_summary_csv': self._create_option_summary_writer(paths['option_summary']),
                'final_summary_csv': self._create_summary_writer(paths['final_summary'])
            }
            
            self.logger.info(f"{len(writers)}個のCSVライターを作成しました")
            return writers
            
        except Exception as e:
            self.logger.error(f"CSVライター作成中にエラー: {e}")
            raise

    def _create_dividend_writer(self, path: Path) -> CSVOutput:
        """配当データ用のCSVライターを作成"""
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'gross_amount', 'tax_amount', 'net_amount',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
            'exchange_rate'
        ])

    def _create_interest_writer(self, path: Path) -> CSVOutput:
        """利子データ用のCSVライターを作成"""
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'gross_amount', 'tax_amount', 'net_amount',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
            'exchange_rate'
        ])

    def _create_stock_writer(self, path: Path) -> CSVOutput:
        """株式取引データ用のCSVライターを作成"""
        return CSVOutput(path, [
            'date', 'account', 'symbol', 'description',
            'action', 'quantity', 'price', 'realized_gain',
            'price_jpy', 'realized_gain_jpy',
            'exchange_rate'
        ])

    def _create_option_writer(self, path: Path) -> CSVOutput:
        """オプション取引データ用のCSVライターを作成"""
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
        """オプション取引サマリー用のCSVライターを作成"""
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
        """最終サマリー用のCSVライターを作成"""
        return CSVOutput(path, [
            'category', 'subcategory',
            'gross_amount_usd', 'tax_amount_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy'
        ])