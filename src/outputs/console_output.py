from typing import Any, List, Dict
import logging
from decimal import Decimal

from ..outputs.base_output import BaseOutput
from ..formatters.base_formatter import BaseFormatter

class ConsoleOutput(BaseOutput):
    """コンソール出力クラス"""
    
    def output(self, data: Any) -> None:
        """データをコンソールに出力"""
        try:
            # サマリーデータの場合
            if isinstance(data, dict) and self._is_summary_data(data):
                self._output_summary(data)
            # レコードリストの場合
            elif isinstance(data, list):
                self._output_record_summary(data)
            # その他のデータ
            else:
                print(str(data))
        
        except Exception as e:
            self.logger.error(f"コンソール出力エラー: {e}")
            print(str(data))

    def _is_summary_data(self, data: Dict) -> bool:
        """サマリーデータかどうかを判定"""
        return all(key in data for key in ['income', 'trading', 'total'])

    def _output_summary(self, summary: Dict) -> None:
        """投資サマリーを出力"""
        print("\n【投資総合レポート】")
        print("=" * 40)
        
        # 収入サマリー
        income = summary.get('income', {})
        print("\n【収入サマリー】")
        print(f"配当総額:     ${income.get('dividend_total', 0):.2f}")
        print(f"利子総額:     ${income.get('interest_total', 0):.2f}")
        print(f"税金総額:     ${income.get('tax_total', 0):.2f}")
        print(f"純収入:       ${income.get('net_total', 0):.2f}")
        
        # 取引サマリー
        trading = summary.get('trading', {})
        print("\n【取引サマリー】")
        print(f"株式取引損益: ${trading.get('stock_gain', 0):.2f}")
        print(f"オプション取引損益: ${trading.get('option_gain', 0):.2f}")
        print(f"オプションプレミアム収入: ${trading.get('premium_income', 0):.2f}")
        print(f"純取引損益:   ${trading.get('net_total', 0):.2f}")
        
        # 総合計
        total = summary.get('total', {})
        print("\n【総合計】")
        print(f"総収入:       ${total.get('total_income', 0):.2f}")
        print(f"総取引損益:   ${total.get('total_trading', 0):.2f}")
        print(f"総合計:       ${total.get('grand_total', 0):.2f}")
        print("=" * 40)

    def _output_record_summary(self, records: List) -> None:
        """レコードの要約を出力"""
        # 配当と利子のレコードを分離
        dividend_records = [r for r in records if self._is_dividend_record(r)]
        interest_records = [r for r in records if self._is_interest_record(r)]
        
        print("\n【投資収入サマリー】")
        print("=" * 40)
        
        # 配当サマリー
        if dividend_records:
            print("\n【配当サマリー】")
            self._output_income_breakdown(dividend_records, '配当')
        
        # 利子サマリー
        if interest_records:
            print("\n【利子サマリー】")
            self._output_income_breakdown(interest_records, '利子')
        
        print("=" * 40)

    def _output_income_breakdown(self, records: List, income_type: str) -> None:
        """収入の詳細を出力"""
        # アカウント別の集計
        account_summary = self._calculate_account_summary(records)
        
        # アカウント別の出力
        for account, summary in account_summary.items():
            if account != 'total':
                print(f"アカウント {account}:")
                print(f"  総{income_type}額:  ${summary['amount']:.2f}")
                print(f"  課税額:      ${summary.get('tax', 0):.2f}")
                print(f"  純{income_type}額:  ${summary['amount'] - summary.get('tax', 0):.2f}")
        
        # 全体の合計（複数アカウントがある場合）
        if len(account_summary) > 2:  # 'total'を含むので
            total = account_summary['total']
            print(f"\n【総{income_type}サマリー】")
            print(f"総{income_type}額:    ${total['amount']:.2f}")
            print(f"総課税額:      ${total.get('tax', 0):.2f}")
            print(f"総純{income_type}額:  ${total['amount'] - total.get('tax', 0):.2f}")

    def _is_dividend_record(self, record: Any) -> bool:
        """配当レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type == 'Dividend'

    def _is_interest_record(self, record: Any) -> bool:
        """利子レコードかどうかを判定"""
        return hasattr(record, 'income_type') and record.income_type != 'Dividend'

    def _calculate_account_summary(self, records: List) -> Dict:
        """アカウント別の収入サマリーを計算"""
        from decimal import Decimal
        from collections import defaultdict
        
        accounts = defaultdict(lambda: {
            'amount': Decimal('0'),
            'tax': Decimal('0')
        })
        
        for record in records:
            account = accounts[record.account_id]
            account['amount'] += record.gross_amount.amount
            account['tax'] += record.tax_amount.amount
        
        # 全体の合計を計算
        total = {'amount': Decimal('0'), 'tax': Decimal('0')}
        for account in accounts.values():
            total['amount'] += account['amount']
            total['tax'] += account['tax']
        
        accounts['total'] = total
        return accounts

class ColorConsoleOutput(ConsoleOutput):
    """カラー対応コンソール出力クラス"""
    
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'GREEN': '\033[92m',
        'WARNING': '\033[93m',
        'RED': '\033[91m',
        'END': '\033[0m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m'
    }

    def _output_summary(self, summary: Dict) -> None:
        """カラー付きサマリー出力"""
        print(f"\n{self.COLORS['HEADER']}【投資総合レポート】{self.COLORS['END']}")
        print("=" * 40)
        
        # 収入サマリー（青色）
        income = summary.get('income', {})
        print(f"\n{self.COLORS['BLUE']}【収入サマリー】{self.COLORS['END']}")
        print(f"配当総額:     ${income.get('dividend_total', 0):.2f}")
        print(f"利子総額:     ${income.get('interest_total', 0):.2f}")
        print(f"税金総額:     ${income.get('tax_total', 0):.2f}")
        print(f"純収入:       ${income.get('net_total', 0):.2f}")
        
        # 取引サマリー（緑色）
        trading = summary.get('trading', {})
        print(f"\n{self.COLORS['GREEN']}【取引サマリー】{self.COLORS['END']}")
        print(f"株式取引損益: ${trading.get('stock_gain', 0):.2f}")
        print(f"オプション取引損益: ${trading.get('option_gain', 0):.2f}")
        print(f"オプションプレミアム収入: ${trading.get('premium_income', 0):.2f}")
        print(f"純取引損益:   ${trading.get('net_total', 0):.2f}")
        
        # 総合計（ボールド）
        total = summary.get('total', {})
        print(f"\n{self.COLORS['BOLD']}【総合計】{self.COLORS['END']}")
        print(f"総収入:       ${total.get('total_income', 0):.2f}")
        print(f"総取引損益:   ${total.get('total_trading', 0):.2f}")
        print(f"総合計:       ${total.get('grand_total', 0):.2f}")
        print("=" * 40)