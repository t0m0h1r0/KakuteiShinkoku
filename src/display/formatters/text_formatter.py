from typing import Dict, Any, List, Union
from decimal import Decimal
from collections import defaultdict

from ..formatters.base import BaseFormatter
from ...core.types.money import Money
from ...core.constants.currency import Currency

class TextFormatter(BaseFormatter):
    """テキスト形式のフォーマッタ"""
    
    def format(self, data: Any) -> str:
        """データをテキスト形式でフォーマット"""
        try:
            if isinstance(data, list):
                return self._format_record_list(data)
            elif isinstance(data, dict):
                if self._is_summary_data(data):
                    return self._format_summary_data(data)
            return str(data)
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            return str(data)

    def _format_record_list(self, records: List) -> str:
        """記録リストのフォーマット"""
        if not records:
            return "No records found"

        # 配当と利子のレコードを分離
        dividend_records = [r for r in records if self._is_dividend_record(r)]
        interest_records = [r for r in records if self._is_interest_record(r)]
        
        # 結果を格納するリスト
        lines = []
        
        # 配当のフォーマット
        if dividend_records:
            lines.extend(self._format_dividend_records(dividend_records))
        
        # 利子のフォーマット
        if interest_records:
            if lines:  # 配当の出力がある場合は空行を追加
                lines.append("")
            lines.extend(self._format_interest_records(interest_records))
        
        return "\n".join(lines)

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'

    def _format_dividend_records(self, records: List) -> List[str]:
        """配当記録のフォーマット"""
        accounts = defaultdict(lambda: {
            'amount': Decimal('0'),
            'tax': Decimal('0')
        })
        
        # アカウントごとに集計
        for record in records:
            accounts[record.account_id]['amount'] += record.gross_amount.amount
            accounts[record.account_id]['tax'] += record.tax_amount.amount

        # 結果の出力
        lines = ["Dividend Income:"]
        for account_id, summary in accounts.items():
            lines.append(f"\nAccount: {account_id}")
            lines.append(f"Dividend Total: ${summary['amount']:.2f}")
            lines.append(f"Tax Total: ${summary['tax']:.2f}")
            net_total = summary['amount'] - summary['tax']
            lines.append(f"Net Total: ${net_total:.2f}")

        # 複数アカウントの場合は合計を表示
        if len(accounts) > 1:
            total_amount = sum(summary['amount'] for summary in accounts.values())
            total_tax = sum(summary['tax'] for summary in accounts.values())
            net_grand_total = total_amount - total_tax
            
            lines.append("\nDividend Total Summary:")
            lines.append(f"Total Dividend: ${total_amount:.2f}")
            lines.append(f"Total Tax: ${total_tax:.2f}")
            lines.append(f"Net Total: ${net_grand_total:.2f}")

        return lines

    def _format_interest_records(self, records: List) -> List[str]:
        """利子記録のフォーマット"""
        accounts = defaultdict(lambda: {
            'amount': Decimal('0'),
            'tax': Decimal('0')
        })
        
        # アカウントごとに集計
        for record in records:
            accounts[record.account_id]['amount'] += record.gross_amount.amount
            accounts[record.account_id]['tax'] += record.tax_amount.amount

        # 結果の出力
        lines = ["Interest Income:"]
        for account_id, summary in accounts.items():
            lines.append(f"\nAccount: {account_id}")
            lines.append(f"Interest Total: ${summary['amount']:.2f}")
            lines.append(f"Tax Total: ${summary['tax']:.2f}")
            net_total = summary['amount'] - summary['tax']
            lines.append(f"Net Total: ${net_total:.2f}")

        # 複数アカウントの場合は合計を表示
        if len(accounts) > 1:
            total_amount = sum(summary['amount'] for summary in accounts.values())
            total_tax = sum(summary['tax'] for summary in accounts.values())
            net_grand_total = total_amount - total_tax
            
            lines.append("\nInterest Total Summary:")
            lines.append(f"Total Interest: ${total_amount:.2f}")
            lines.append(f"Total Tax: ${total_tax:.2f}")
            lines.append(f"Net Total: ${net_grand_total:.2f}")

        return lines

    def _is_summary_data(self, data: Dict) -> bool:
        """サマリーデータかどうかを判定"""
        return ('income' in data and 'trading' in data and 'total' in data) or \
               ('accounts' in data and 'total' in data)

    def _format_summary_data(self, data: Dict) -> str:
        """サマリーデータのフォーマット"""
        if 'income' in data:
            return self._format_full_summary(data)
        return self._format_account_summary(data)

    def _format_full_summary(self, data: Dict) -> str:
        """総合サマリーのフォーマット"""
        income = data['income']
        trading = data['trading']
        total = data['total']
        
        lines = ["Investment Summary Report"]
        lines.append("-" * 30)
        
        # 収入サマリー
        lines.append("\nIncome Summary:")
        lines.append(f"Dividend Total: ${income['dividend_total']:.2f}")
        lines.append(f"Interest Total: ${income['interest_total']:.2f}")
        lines.append(f"Tax Total: ${income['tax_total']:.2f}")
        lines.append(f"Net Income: ${income['net_total']:.2f}")
        
        # 取引サマリー
        lines.append("\nTrading Summary:")
        lines.append(f"Stock Trading Gain: ${trading['stock_gain']:.2f}")
        lines.append(f"Option Trading Gain: ${trading['option_gain']:.2f}")
        lines.append(f"Option Premium Income: ${trading['premium_income']:.2f}")
        lines.append(f"Net Trading Gain: ${trading['net_total']:.2f}")
        
        # 総合計
        lines.append("\nTotal Summary:")
        lines.append(f"Total Income: ${total['total_income']:.2f}")
        lines.append(f"Total Trading: ${total['total_trading']:.2f}")
        lines.append(f"Grand Total: ${total['grand_total']:.2f}")
        
        return "\n".join(lines)

    def _format_account_summary(self, data: Dict) -> str:
        """アカウント別サマリーのフォーマット"""
        lines = []
        
        for account_id, summary in data['accounts'].items():
            lines.append(f"\nAccount: {account_id}")
            
            # 配当情報の表示
            if 'dividend' in summary and summary['dividend'] > 0:
                lines.append(f"Dividend Total: ${summary['dividend']:.2f}")
            
            # 利子情報の表示
            if 'interest' in summary and summary['interest'] > 0:
                lines.append(f"Interest Total: ${summary['interest']:.2f}")
            
            # 税金情報の表示
            if 'tax' in summary and summary['tax'] > 0:
                lines.append(f"Tax Total: ${summary['tax']:.2f}")
            
            net_total = summary.get('dividend', Decimal('0')) + \
                       summary.get('interest', Decimal('0')) - \
                       summary.get('tax', Decimal('0'))
            lines.append(f"Net Total: ${net_total:.2f}")
        
        return "\n".join(lines)