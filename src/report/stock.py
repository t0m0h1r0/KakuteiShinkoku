from typing import Dict, Any, List

from ..report.interfaces import BaseReportGenerator
from ..processors.stock.record import StockTradeRecord

class StockTradeReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        stock_records: List[StockTradeRecord] = data.get('stock_records', [])
        
        return [{
            'date': record.trade_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'price': record.price.usd,
            'realized_gain': record.realized_gain.usd,
            'fees': record.fees.usd,
            'price_jpy': record.price.jpy,
            'realized_gain_jpy': record.realized_gain.jpy,
            'fees_jpy': record.fees.jpy,
            'exchange_rate': record.exchange_rate
        } for record in stock_records]
