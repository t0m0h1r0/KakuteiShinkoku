from typing import Dict, Any, List, Union
from decimal import Decimal
from collections import defaultdict
from ..formatters.base import BaseFormatter
from ...core.types.money import Money
from ...core.constants.currency import Currency

class TextFormatter(BaseFormatter):
    """テキスト形式のフォーマッタ"""
    
    def format(self, data: Union[Dict[str, Dict[str, Any]], List]) -> str:
        """データをテキスト形式でフォーマット"""
        if isinstance(data, list):
            return self._format_record_list(data)
        return self._format_summary_dict(data)

    def _format_record_list(self, records: List) -> str:
        """レコードリストのフォーマット"""
        # レコードを口座ごとにグループ化
        accounts = defaultdict(list)
        for record in records:
            accounts[record.account_id].append(record)

        output = []
        total_summary = defaultdict(lambda: Money(Decimal('0')))

        # 口座別のサマリー
        for account, account_records in accounts.items():
            output.append(f"\nAccount: {account}")
            account_summary = self._calculate_account_summary(account_records)
            output.append(self._format_summary_section(account_summary))
            
            # 合計に加算
            for key, value in account_summary.items():
                if isinstance(value, Money):
                    total_summary[key] += value

        # 全体の合計
        output.append("\nTotal Summary:")
        output.append(self._format_summary_section(dict(total_summary)))

        return "\n".join(output)

    def _calculate_account_summary(self, records: List) -> Dict[str, Any]:
        """口座別サマリーの計算"""
        summary = {
            'Dividend': Money(Decimal('0')),
            'Interest': Money(Decimal('0')),
            'CD Interest': Money(Decimal('0')),
            'Tax': Money(Decimal('0')),
            'dividend_jpy': Money(Decimal('0'), Currency.JPY),
            'interest_jpy': Money(Decimal('0'), Currency.JPY),
            'cd_interest_jpy': Money(Decimal('0'), Currency.JPY),
            'tax_jpy': Money(Decimal('0'), Currency.JPY)
        }

        for record in records:
            amount = record.gross_amount
            tax = record.tax_amount
            exchange_rate = record.exchange_rate

            if record.income_type == 'Dividend':
                summary['Dividend'] += amount
                summary['dividend_jpy'] += Money(amount.amount * exchange_rate, Currency.JPY)
            elif record.income_type == 'CD Interest':
                summary['CD Interest'] += amount
                summary['cd_interest_jpy'] += Money(amount.amount * exchange_rate, Currency.JPY)
            else:  # Other Interest
                summary['Interest'] += amount
                summary['interest_jpy'] += Money(amount.amount * exchange_rate, Currency.JPY)

            summary['Tax'] += tax
            summary['tax_jpy'] += Money(tax.amount * exchange_rate, Currency.JPY)

        return summary

    def _format_summary_dict(self, data: Dict[str, Dict[str, Any]]) -> str:
        """サマリー辞書のフォーマット"""
        output = []
        
        # アカウント別サマリー
        for account, summary in data.items():
            output.append(f"\nAccount: {account}")
            output.append(self._format_summary_section(summary))
        
        # 合計サマリー
        if data:
            output.append("\nTotal Summary:")
            total_summary = self._calculate_total_summary(data)
            output.append(self._format_summary_section(total_summary))
        
        return "\n".join(output)

    def _format_summary_section(self, summary: Dict[str, Any]) -> str:
        """サマリーセクションのフォーマット"""
        lines = []
        
        if summary.get('principal', Money(Decimal('0'))).amount > 0:
            lines.append(
                f"CD Principal: {self._format_currency(summary['principal'])}"
            )
        
        if summary.get('CD Interest', Money(Decimal('0'))).amount > 0:
            lines.append(
                f"CD Interest Total: {self._format_currency(summary['CD Interest'])} "
                f"(¥{self._format_money(summary['cd_interest_jpy'], 0)})"
            )
        
        lines.append(
            f"Dividend Total: {self._format_currency(summary['Dividend'])} "
            f"(¥{self._format_money(summary['dividend_jpy'], 0)})"
        )
        
        lines.append(
            f"Other Interest Total: {self._format_currency(summary['Interest'])} "
            f"(¥{self._format_money(summary['interest_jpy'], 0)})"
        )
        
        lines.append(
            f"Withholding Tax Total: {self._format_currency(summary['Tax'])} "
            f"(¥{self._format_money(summary['tax_jpy'], 0)})"
        )
        
        # Net Income
        net_income = self._calculate_net_income(summary)
        lines.append(
            f"Net Income Total: {self._format_currency(net_income['usd'])} "
            f"(¥{self._format_money(net_income['jpy'], 0)})"
        )
        
        return "\n".join(lines)

    def _calculate_net_income(self, summary: Dict[str, Any]) -> Dict[str, Money]:
        """純収入の計算"""
        total_income_usd = Money(
            summary['Dividend'].amount +
            summary['Interest'].amount +
            summary.get('CD Interest', Money(Decimal('0'))).amount
        )
        
        total_income_jpy = Money(
            summary['dividend_jpy'].amount +
            summary['interest_jpy'].amount +
            summary.get('cd_interest_jpy', Money(Decimal('0'))).amount,
            Currency.JPY
        )
        
        net_usd = total_income_usd - summary['Tax']
        net_jpy = Money(total_income_jpy.amount - summary['tax_jpy'].amount, Currency.JPY)
        
        return {'usd': net_usd, 'jpy': net_jpy}

    def _calculate_total_summary(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """合計サマリーの計算"""
        total = {
            'principal': Money(Decimal('0')),
            'Dividend': Money(Decimal('0')),
            'Interest': Money(Decimal('0')),
            'CD Interest': Money(Decimal('0')),
            'Tax': Money(Decimal('0')),
            'dividend_jpy': Money(Decimal('0'), Currency.JPY),
            'interest_jpy': Money(Decimal('0'), Currency.JPY),
            'cd_interest_jpy': Money(Decimal('0'), Currency.JPY),
            'tax_jpy': Money(Decimal('0'), Currency.JPY)
        }
        
        for summary in data.values():
            for key in total.keys():
                if key in summary:
                    total[key] = Money(
                        total[key].amount + summary[key].amount,
                        total[key].currency
                    )
        
        return total