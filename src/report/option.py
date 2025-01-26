from typing import Dict, Any, List

from ..report.interfaces import BaseReportGenerator
from ..processors.option.record import OptionTradeRecord

class OptionTradeReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        option_records: List[OptionTradeRecord] = data.get('option_records', [])
        
        return [{
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol,
            'description': record.description,
            'action': record.action,
            'quantity': record.quantity,
            'option_type': record.option_type,
            'strike_price': float(record.strike_price),
            'expiry_date': record.expiry_date.strftime('%Y-%m-%d'),
            'underlying': record.underlying,
            'price': record.price.usd,
            'fees': record.fees.usd,
            'trading_pnl': record.trading_pnl.usd,
            'premium_pnl': record.premium_pnl.usd,
            'price_jpy': record.price.jpy,
            'fees_jpy': record.fees.jpy,
            'trading_pnl_jpy': record.trading_pnl.jpy,
            'premium_pnl_jpy': record.premium_pnl.jpy,
            'exchange_rate': record.exchange_rate,
            'position_type': record.position_type,
            'is_closed': record.is_closed,
            'is_expired': record.is_expired,
            'is_assigned': record.is_assigned
        } for record in option_records]
