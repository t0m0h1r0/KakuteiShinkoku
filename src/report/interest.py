from typing import Dict, Any, List

from ..report.interfaces import BaseReportGenerator
from ..processors.interest.record import InterestTradeRecord

class InterestReportGenerator(BaseReportGenerator):
    def generate(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        interest_records: List[InterestTradeRecord] = data.get('interest_records', [])
        
        return [{
            'date': record.record_date,
            'account': record.account_id,
            'symbol': record.symbol or '',
            'description': record.description,
            'income_type': record.income_type,
            'action_type': record.action_type,
            'gross_amount': record.gross_amount.usd,
            'tax_amount': record.tax_amount.usd,
            'net_amount': record.net_amount.usd,
            'gross_amount_jpy': record.gross_amount.jpy,
            'tax_amount_jpy': record.tax_amount.jpy,
            'net_amount_jpy': record.net_amount.jpy,
            'exchange_rate': record.exchange_rate
        } for record in interest_records]
