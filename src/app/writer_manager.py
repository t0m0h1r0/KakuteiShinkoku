from typing import Dict
from ..config.settings import OUTPUT_FILES
from ..outputs.csv_writer import CSVWriter

class WriterManager:
    """ライター管理クラス"""
    
    @staticmethod
    def create_writers(display_outputs) -> Dict:
        """CSVライターとコンソール出力の設定"""
        return {
            'console': display_outputs['console'],
            'dividend_csv': CSVWriter(
                OUTPUT_FILES['dividend_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'gross_amount', 'tax_amount', 'net_amount',
                    'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
                    'exchange_rate'
                ]
            ),
            'interest_csv': CSVWriter(
                OUTPUT_FILES['interest_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'action', 'gross_amount', 'tax_amount', 'net_amount',
                    'gross_amount_jpy', 'tax_amount_jpy', 'net_amount_jpy',
                    'exchange_rate'
                ]
            ),
            'stock_trade_csv': CSVWriter(
                OUTPUT_FILES['stock_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'action', 'quantity', 'price', 'realized_gain',
                    'price_jpy', 'realized_gain_jpy',
                    'exchange_rate'
                ]
            ),
            'option_trade_csv': CSVWriter(
                OUTPUT_FILES['option_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'action', 'quantity', 'option_type', 'strike_price',
                    'expiry_date', 'underlying',
                    'price', 'fees', 'trading_pnl', 'premium_pnl',
                    'price_jpy', 'fees_jpy', 'trading_pnl_jpy', 'premium_pnl_jpy',
                    'exchange_rate', 'position_type', 'is_closed', 'is_expired'
                ]
            ),
            'option_summary_csv': CSVWriter(
                OUTPUT_FILES['option_summary'],
                fieldnames=[
                    'account', 'symbol', 'description', 'underlying',
                    'option_type', 'strike_price', 'expiry_date',
                    'open_date', 'close_date', 'status',
                    'initial_quantity', 'remaining_quantity',
                    'trading_pnl', 'premium_pnl', 'total_fees',
                    'trading_pnl_jpy', 'premium_pnl_jpy', 'total_fees_jpy',
                    'exchange_rate'
                ]
            ),
            'final_summary_csv': CSVWriter(
                OUTPUT_FILES['final_summary'],
                fieldnames=[
                    'category',             # 取引カテゴリ（配当、利子、株式、オプションなど）
                    'subcategory',          # サブカテゴリ（オプションの場合：譲渡益、プレミアムなど）
                    'gross_amount_usd',     # 総額（USD）
                    'tax_amount_usd',       # 税額（USD）
                    'net_amount_usd',       # 純額（USD）
                    'gross_amount_jpy',     # 総額（JPY）
                    'tax_amount_jpy',       # 税額（JPY）
                    'net_amount_jpy',       # 純額（JPY）
                    'average_exchange_rate' # 平均為替レート
                ]
            )
        }