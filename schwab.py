from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import csv
import json
import logging

@dataclass
class Transaction:
    date: str
    account: str
    symbol: str
    description: str
    amount: Decimal
    action: str
    
@dataclass
class DividendRecord:
    date: str
    account: str
    symbol: str
    description: str
    type: str
    gross_amount: Decimal
    tax: Decimal
    exchange_rate: Decimal
    reinvested: bool

class ExchangeRateManager:
    def __init__(self, filename: str = 'HistoricalPrices.csv'):
        self.rates: Dict[str, Decimal] = {}
        self._load_rates(filename)

    def _load_rates(self, filename: str) -> None:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    date_str = self._normalize_date(row['Date'].strip())
                    self.rates[date_str] = Decimal(row[' Close'])
        except FileNotFoundError:
            logging.warning(f"為替レートファイル {filename} が見つかりません")
        except Exception as e:
            logging.error(f"為替レートファイルの読み込み中にエラー: {e}")

    def _normalize_date(self, date_str: str) -> str:
        parts = date_str.split('/')
        if len(parts[2]) == 2:
            parts[2] = f"20{parts[2]}"
        return '/'.join(parts)

    def get_rate(self, date: str) -> Decimal:
        if not self.rates:
            return Decimal('150.0')
            
        if date in self.rates:
            return self.rates[date]
            
        target_date = datetime.strptime(date, '%m/%d/%Y')
        dated_rates = {
            datetime.strptime(d, '%m/%d/%Y'): r 
            for d, r in self.rates.items()
        }
        
        previous_dates = [d for d in dated_rates.keys() if d <= target_date]
        if not previous_dates:
            return Decimal(str(list(self.rates.values())[0]))
            
        return dated_rates[max(previous_dates)]

class TransactionProcessor:
    def __init__(self, exchange_rate_manager: ExchangeRateManager):
        self.exchange_rate_manager = exchange_rate_manager

    def load_transactions(self, filename: Path) -> List[Transaction]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                account = filename.stem
                return [
                    Transaction(
                        date=trans['Date'].split(' as of ')[0],
                        account=account,
                        symbol=trans['Symbol'],
                        description=trans['Description'],
                        amount=Decimal(trans['Amount'].replace('$', '').replace(',', '')) if trans['Amount'] else Decimal('0'),
                        action=trans['Action']
                    )
                    for trans in data['BrokerageTransactions']
                ]
        except Exception as e:
            logging.error(f"ファイル {filename} の読み込み中にエラー: {e}")
            return []

    def process_transactions(self, transactions: List[Transaction]) -> List[DividendRecord]:
        temp_records: Dict[Tuple[str, str, str], DividendRecord] = {}
        
        for trans in transactions:
            if not self._is_relevant_transaction(trans):
                continue
                
            key = (trans.date, trans.symbol if trans.symbol else trans.description, trans.account)
            
            if key not in temp_records:
                temp_records[key] = self._create_dividend_record(trans)
            
            self._update_record(temp_records[key], trans)
        
        return sorted(
            [r for r in temp_records.values() if r.gross_amount > 0 or r.tax > 0],
            key=lambda x: datetime.strptime(x.date, '%m/%d/%Y')
        )

    def _is_relevant_transaction(self, trans: Transaction) -> bool:
        return trans.action in [
            'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
            'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'
        ] or (trans.action in ['NRA Tax Adj', 'Pr Yr NRA Tax'] and trans.amount < 0)

    def _create_dividend_record(self, trans: Transaction) -> DividendRecord:
        return DividendRecord(
            date=trans.date,
            account=trans.account,
            symbol=trans.symbol,
            description=trans.description,
            type='Interest' if any(word in trans.action for word in ['Interest', 'Bank']) else 'Dividend',
            gross_amount=Decimal('0'),
            tax=Decimal('0'),
            exchange_rate=self.exchange_rate_manager.get_rate(trans.date),
            reinvested=False
        )

    def _update_record(self, record: DividendRecord, trans: Transaction) -> None:
        if trans.action in ['NRA Tax Adj', 'Pr Yr NRA Tax']:
            record.tax = abs(trans.amount)
        else:
            record.gross_amount = trans.amount
            if trans.action == 'Reinvest Dividend':
                record.reinvested = True

class ReportGenerator:
    @staticmethod
    def generate_csv(records: List[DividendRecord], filename: str) -> None:
        fieldnames = [
            'date', 'account', 'symbol', 'description', 'type',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(ReportGenerator._format_record(record))

    @staticmethod
    def _format_record(record: DividendRecord) -> Dict:
        gross_usd = round(record.gross_amount, 3)
        tax_usd = round(record.tax, 3)
        net_usd = round(gross_usd - tax_usd, 3)
        
        gross_jpy = round(record.gross_amount * record.exchange_rate)
        tax_jpy = round(record.tax * record.exchange_rate)
        net_jpy = round(gross_jpy - tax_jpy)
        
        return {
            'date': record.date,
            'account': record.account,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.type,
            'gross_amount_usd': gross_usd,
            'tax_usd': tax_usd,
            'net_amount_usd': net_usd,
            'exchange_rate': record.exchange_rate,
            'gross_amount_jpy': gross_jpy,
            'tax_jpy': tax_jpy,
            'net_amount_jpy': net_jpy,
            'reinvested': 'Yes' if record.reinvested else 'No'
        }

    @staticmethod
    def print_summary(records: List[DividendRecord]) -> None:
        account_summary = {}
        
        for record in records:
            if record.account not in account_summary:
                account_summary[record.account] = {
                    'dividend_usd': Decimal('0'),
                    'interest_usd': Decimal('0'),
                    'tax_usd': Decimal('0'),
                    'dividend_jpy': Decimal('0'),
                    'interest_jpy': Decimal('0'),
                    'tax_jpy': Decimal('0')
                }
            
            summary = account_summary[record.account]
            if record.type == 'Dividend':
                summary['dividend_usd'] += record.gross_amount
                summary['dividend_jpy'] += record.gross_amount * record.exchange_rate
            else:
                summary['interest_usd'] += record.gross_amount
                summary['interest_jpy'] += record.gross_amount * record.exchange_rate
            summary['tax_usd'] += record.tax
            summary['tax_jpy'] += record.tax * record.exchange_rate

        ReportGenerator._print_account_summaries(account_summary)
        ReportGenerator._print_total_summary(account_summary)

    @staticmethod
    def _print_account_summaries(account_summary: Dict) -> None:
        print("\n=== アカウント別集計 ===")
        for account, summary in account_summary.items():
            print(f"\nアカウント: {account}")
            print(f"配当金合計: ${summary['dividend_usd']:,.3f} (¥{int(summary['dividend_jpy']):,})")
            print(f"利子合計: ${summary['interest_usd']:,.3f} (¥{int(summary['interest_jpy']):,})")
            print(f"源泉徴収合計: ${summary['tax_usd']:,.3f} (¥{int(summary['tax_jpy']):,})")
            net_usd = summary['dividend_usd'] + summary['interest_usd'] - summary['tax_usd']
            net_jpy = summary['dividend_jpy'] + summary['interest_jpy'] - summary['tax_jpy']
            print(f"手取り合計: ${net_usd:,.3f} (¥{int(net_jpy):,})")

    @staticmethod
    def _print_total_summary(account_summary: Dict) -> None:
        totals = {
            'dividend_usd': sum(s['dividend_usd'] for s in account_summary.values()),
            'interest_usd': sum(s['interest_usd'] for s in account_summary.values()),
            'tax_usd': sum(s['tax_usd'] for s in account_summary.values()),
            'dividend_jpy': sum(s['dividend_jpy'] for s in account_summary.values()),
            'interest_jpy': sum(s['interest_jpy'] for s in account_summary.values()),
            'tax_jpy': sum(s['tax_jpy'] for s in account_summary.values())
        }
        
        print("\n=== 総合計 ===")
        print(f"配当金合計: ${totals['dividend_usd']:,.3f} (¥{int(totals['dividend_jpy']):,})")
        print(f"利子合計: ${totals['interest_usd']:,.3f} (¥{int(totals['interest_jpy']):,})")
        print(f"源泉徴収合計: ${totals['tax_usd']:,.3f} (¥{int(totals['tax_jpy']):,})")
        net_usd = totals['dividend_usd'] + totals['interest_usd'] - totals['tax_usd']
        net_jpy = totals['dividend_jpy'] + totals['interest_jpy'] - totals['tax_jpy']
        print(f"手取り合計: ${net_usd:,.3f} (¥{int(net_jpy):,})")

def main():
    try:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        exchange_rate_manager = ExchangeRateManager()
        processor = TransactionProcessor(exchange_rate_manager)
        
        json_files = list(Path('.').glob('*.json'))
        if not json_files:
            logging.error("処理対象のJSONファイルが見つかりません")
            return
        
        all_transactions = []
        for file in json_files:
            logging.info(f"ファイル {file} を処理中...")
            transactions = processor.load_transactions(file)
            all_transactions.extend(transactions)
        
        dividend_records = processor.process_transactions(all_transactions)
        
        output_filename = 'dividend_tax_history.csv'
        ReportGenerator.generate_csv(dividend_records, output_filename)
        
        logging.info(f"\n{len(json_files)}個のファイルから{len(dividend_records)}件のレコードを処理しました")
        logging.info(f"結果は {output_filename} に出力されました")
        
        ReportGenerator.print_summary(dividend_records)
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
