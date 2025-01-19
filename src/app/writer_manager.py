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
                    'type', 'gross_amount', 'tax_amount', 'net_amount'
                ]
            ),
            'interest_csv': CSVWriter(
                OUTPUT_FILES['interest_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'action', 'gross_amount', 'tax_amount', 'net_amount'
                ]
            ),
            'stock_trade_csv': CSVWriter(
                OUTPUT_FILES['stock_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 'description',
                    'type', 'action', 'quantity', 'price', 'realized_gain'
                ]
            ),
            'option_trade_csv': CSVWriter(
                OUTPUT_FILES['option_trade_history'],
                fieldnames=[
                    'date', 'account', 'symbol', 
                    'description', 'action', 'quantity', 'price'
                ]
            ),
            'option_premium_csv': CSVWriter(
                OUTPUT_FILES['option_premium'],
                fieldnames=[
                    'account', 'symbol', 'description', 
                    'fees_total', 'final_premium', 
                    'status', 'close_date'
                ]
            ),
            'profit_loss_csv': CSVWriter(
                OUTPUT_FILES['profit_loss_summary'],
                fieldnames=[
                    'Account', 'Dividend', 'Interest', 'Tax', 'Net Total'
                ]
            )
        }