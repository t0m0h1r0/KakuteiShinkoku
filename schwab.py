from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
import csv
import json
import logging
from abc import ABC, abstractmethod

# Constants
DEFAULT_EXCHANGE_RATE = Decimal('150.0')
DATE_FORMAT = '%m/%d/%Y'
CSV_ENCODING = 'utf-8'

@dataclass(frozen=True)
class Transaction:
    """取引情報を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    amount: Decimal
    action: str

@dataclass(frozen=True)
class DividendRecord:
    """配当に関する記録を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    type: str
    gross_amount: Decimal
    tax: Decimal
    exchange_rate: Decimal
    reinvested: bool

    @property
    def net_amount_usd(self) -> Decimal:
        """米ドルでの手取り額を計算"""
        return round(self.gross_amount - self.tax, 2)

    @property
    def net_amount_jpy(self) -> Decimal:
        """日本円での手取り額を計算"""
        return round((self.gross_amount - self.tax) * self.exchange_rate)

class ExchangeRateManager:
    """為替レートの管理を行うクラス"""
    """WSJのデータを使用"""
    """https://www.wsj.com/market-data/quotes/fx/USDJPY/historical-prices"""
    
    def __init__(self, filename: str = 'HistoricalPrices.csv'):
        self.rates: Dict[str, Decimal] = {}
        self._load_rates(filename)

    def _load_rates(self, filename: str) -> None:
        """為替レートファイルを読み込む"""
        try:
            with Path(filename).open('r', encoding=CSV_ENCODING) as f:
                reader = csv.DictReader(f)
                self.rates = {
                    self._normalize_date(row['Date'].strip()): Decimal(row[' Close'])
                    for row in reader
                }
        except FileNotFoundError:
            logging.warning(f"為替レートファイル {filename} が見つかりません")
        except Exception as e:
            logging.error(f"為替レートファイルの読み込み中にエラー: {e}")

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """日付文字列を標準形式に変換"""
        month, day, year = date_str.split('/')
        return f"{month}/{day}/{'20' + year if len(year) == 2 else year}"

    def get_rate(self, date: str) -> Decimal:
        """指定日付の為替レートを取得"""
        if not self.rates:
            return DEFAULT_EXCHANGE_RATE

        if date in self.rates:
            return self.rates[date]

        target_date = datetime.strptime(date, DATE_FORMAT)
        dated_rates = {
            datetime.strptime(d, DATE_FORMAT): r 
            for d, r in self.rates.items()
        }

        previous_dates = [d for d in dated_rates.keys() if d <= target_date]
        return dated_rates[max(previous_dates)] if previous_dates else list(self.rates.values())[0]

# ... 前半部分は同じ ...

class TransactionProcessor:
    """取引データの処理を行うクラス"""

    DIVIDEND_ACTIONS = {
        'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
        'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'
    }
    TAX_ACTIONS = {'NRA Tax Adj', 'Pr Yr NRA Tax'}

    def __init__(self, exchange_rate_manager: ExchangeRateManager):
        self.exchange_rate_manager = exchange_rate_manager

    def load_transactions(self, filename: Path) -> List[Transaction]:
        """JSONファイルから取引データを読み込む"""
        try:
            with filename.open('r', encoding=CSV_ENCODING) as f:
                data = json.load(f)
                return [
                    self._create_transaction(trans, filename.stem)
                    for trans in data['BrokerageTransactions']
                ]
        except Exception as e:
            logging.error(f"ファイル {filename} の読み込み中にエラー: {e}")
            return []

    def _create_transaction(self, trans_data: Dict, account: str) -> Transaction:
        """取引データからTransactionオブジェクトを作成"""
        return Transaction(
            date=trans_data['Date'].split(' as of ')[0],
            account=account,
            symbol=trans_data['Symbol'],
            description=trans_data['Description'],
            amount=self._parse_amount(trans_data['Amount']),
            action=trans_data['Action']
        )

    @staticmethod
    def _parse_amount(amount_str: Optional[str]) -> Decimal:
        """金額文字列をDecimal型に変換"""
        if not amount_str:
            return Decimal('0')
        return Decimal(amount_str.replace('$', '').replace(',', ''))

    def process_transactions(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """取引データを処理し配当記録を生成"""
        record_dict: Dict[Tuple[str, str, str], Dict] = {}
        
        for trans in transactions:
            if not self._is_relevant_transaction(trans):
                continue

            key = (trans.date, trans.symbol or trans.description, trans.account)
            
            if key not in record_dict:
                record_dict[key] = {
                    'date': trans.date,
                    'account': trans.account,
                    'symbol': trans.symbol,
                    'description': trans.description,
                    'type': 'Interest' if any(word in trans.action for word in ['Interest', 'Bank']) else 'Dividend',
                    'gross_amount': Decimal('0'),
                    'tax': Decimal('0'),
                    'exchange_rate': self.exchange_rate_manager.get_rate(trans.date),
                    'reinvested': False
                }
            
            self._update_record_dict(record_dict[key], trans)
        
        # 辞書からDividendRecordオブジェクトを生成
        dividend_records = [
            DividendRecord(**record_data)
            for record_data in record_dict.values()
            if record_data['gross_amount'] > 0 or record_data['tax'] > 0
        ]
        
        return sorted(
            dividend_records,
            key=lambda x: datetime.strptime(x.date, DATE_FORMAT)
        )

    def _is_relevant_transaction(self, trans: Transaction) -> bool:
        """処理対象となる取引かどうかを判定"""
        return (trans.action in self.DIVIDEND_ACTIONS or
                (trans.action in self.TAX_ACTIONS and trans.amount < 0))

    def _update_record_dict(self, record_data: Dict, trans: Transaction) -> None:
        """記録データを更新"""
        if trans.action in self.TAX_ACTIONS:
            record_data['tax'] = abs(trans.amount)
        else:
            record_data['gross_amount'] = trans.amount
            if trans.action == 'Reinvest Dividend':
                record_data['reinvested'] = True

class ReportWriter(ABC):
    """レポート出力の基底クラス"""
    
    @abstractmethod
    def write(self, records: List[DividendRecord]) -> None:
        """レポートを出力する"""
        pass

class CSVReportWriter(ReportWriter):
    """CSV形式でレポートを出力するクラス"""

    def __init__(self, filename: str):
        self.filename = filename

    def write(self, records: List[DividendRecord]) -> None:
        """CSVファイルにレポートを出力"""
        fieldnames = [
            'date', 'account', 'symbol', 'description', 'type',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'exchange_rate', 'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'reinvested'
        ]
        
        with Path(self.filename).open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(self._format_record(record))

    @staticmethod
    def _format_record(record: DividendRecord) -> Dict:
        """配当記録をCSV出力用に整形"""
        return {
            'date': record.date,
            'account': record.account,
            'symbol': record.symbol,
            'description': record.description,
            'type': record.type,
            'gross_amount_usd': round(record.gross_amount, 2),
            'tax_usd': round(record.tax, 2),
            'net_amount_usd': record.net_amount_usd,
            'exchange_rate': record.exchange_rate,
            'gross_amount_jpy': round(record.gross_amount * record.exchange_rate),
            'tax_jpy': round(record.tax * record.exchange_rate),
            'net_amount_jpy': record.net_amount_jpy,
            'reinvested': 'Yes' if record.reinvested else 'No'
        }

class ConsoleReportWriter(ReportWriter):
    """コンソールにレポートを出力するクラス"""

    def write(self, records: List[DividendRecord]) -> None:
        """アカウント別サマリーと総合計を出力"""
        account_summary = self._create_account_summary(records)
        self._print_account_summaries(account_summary)
        self._print_total_summary(account_summary)

    def _create_account_summary(self, records: List[DividendRecord]) -> Dict:
        """アカウント別の集計を作成"""
        summary = {}
        for record in records:
            if record.account not in summary:
                summary[record.account] = self._create_empty_summary()
            
            self._update_summary(summary[record.account], record)
        return summary

    @staticmethod
    def _create_empty_summary() -> Dict:
        """新しい集計辞書を作成"""
        return {
            'dividend_usd': Decimal('0'),
            'interest_usd': Decimal('0'),
            'tax_usd': Decimal('0'),
            'dividend_jpy': Decimal('0'),
            'interest_jpy': Decimal('0'),
            'tax_jpy': Decimal('0')
        }

    @staticmethod
    def _update_summary(summary: Dict, record: DividendRecord) -> None:
        """集計を更新"""
        if record.type == 'Dividend':
            summary['dividend_usd'] += record.gross_amount
            summary['dividend_jpy'] += record.gross_amount * record.exchange_rate
        else:
            summary['interest_usd'] += record.gross_amount
            summary['interest_jpy'] += record.gross_amount * record.exchange_rate
        summary['tax_usd'] += record.tax
        summary['tax_jpy'] += record.tax * record.exchange_rate

    def _print_account_summaries(self, account_summary: Dict) -> None:
        """アカウント別の集計を出力"""
        print("\n=== アカウント別集計 ===")
        for account, summary in account_summary.items():
            print(f"\nアカウント: {account}")
            self._print_summary_details(summary)

    def _print_total_summary(self, account_summary: Dict) -> None:
        """総合計を出力"""
        totals = {
            key: sum(s[key] for s in account_summary.values())
            for key in self._create_empty_summary().keys()
        }
        
        print("\n=== 総合計 ===")
        self._print_summary_details(totals)

    @staticmethod
    def _print_summary_details(summary: Dict) -> None:
        """集計の詳細を出力"""
        print(f"配当金合計: ${summary['dividend_usd']:,.2f} (¥{int(summary['dividend_jpy']):,})")
        print(f"利子合計: ${summary['interest_usd']:,.2f} (¥{int(summary['interest_jpy']):,})")
        print(f"源泉徴収合計: ${summary['tax_usd']:,.2f} (¥{int(summary['tax_jpy']):,})")
        
        net_usd = summary['dividend_usd'] + summary['interest_usd'] - summary['tax_usd']
        net_jpy = summary['dividend_jpy'] + summary['interest_jpy'] - summary['tax_jpy']
        print(f"手取り合計: ${net_usd:,.2f} (¥{int(net_jpy):,})")

# ... 前半部分は同じ ...

class SymbolSummaryWriter(ReportWriter):
    """シンボル別サマリーをCSV形式で出力するクラス"""
    
    def __init__(self, filename: str):
        self.filename = filename

    def write(self, records: List[DividendRecord]) -> None:
        """シンボル別サマリーをCSVファイルに出力"""
        symbol_summary = self._create_symbol_summary(records)
        self._write_to_csv(symbol_summary)

    def _create_symbol_summary(self, records: List[DividendRecord]) -> List[Dict]:
        """シンボル別の集計を作成"""
        summary_dict: Dict[str, Dict] = {}
        
        for record in records:
            symbol_key = record.symbol if record.symbol else record.description
            
            if symbol_key not in summary_dict:
                summary_dict[symbol_key] = {
                    'symbol': symbol_key,
                    'description': record.description,
                    'type': record.type,
                    'dividend_usd': Decimal('0'),
                    'interest_usd': Decimal('0'),
                    'tax_usd': Decimal('0'),
                    'dividend_jpy': Decimal('0'),
                    'interest_jpy': Decimal('0'),
                    'tax_jpy': Decimal('0'),
                    'transaction_count': 0
                }
            
            summary = summary_dict[symbol_key]
            summary['transaction_count'] += 1
            
            if record.type == 'Dividend':
                summary['dividend_usd'] += record.gross_amount
                summary['dividend_jpy'] += record.gross_amount * record.exchange_rate
            else:
                summary['interest_usd'] += record.gross_amount
                summary['interest_jpy'] += record.gross_amount * record.exchange_rate
            
            summary['tax_usd'] += record.tax
            summary['tax_jpy'] += record.tax * record.exchange_rate

        # 総額の大きい順にソート
        return sorted(
            summary_dict.values(),
            key=lambda x: x['dividend_usd'] + x['interest_usd'],
            reverse=True
        )

    def _write_to_csv(self, summary_data: List[Dict]) -> None:
        """サマリーデータをCSVファイルに出力"""
        fieldnames = [
            'symbol', 'description', 'type',
            'gross_amount_usd', 'tax_usd', 'net_amount_usd',
            'gross_amount_jpy', 'tax_jpy', 'net_amount_jpy',
            'transaction_count'
        ]
        
        with Path(self.filename).open('w', newline='', encoding=CSV_ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for summary in summary_data:
                gross_usd = summary['dividend_usd'] + summary['interest_usd']
                tax_usd = summary['tax_usd']
                net_usd = gross_usd - tax_usd
                
                gross_jpy = summary['dividend_jpy'] + summary['interest_jpy']
                tax_jpy = summary['tax_jpy']
                net_jpy = gross_jpy - tax_jpy
                
                writer.writerow({
                    'symbol': summary['symbol'],
                    'description': summary['description'],
                    'type': summary['type'],
                    'gross_amount_usd': round(gross_usd, 2),
                    'tax_usd': round(tax_usd, 2),
                    'net_amount_usd': round(net_usd, 2),
                    'gross_amount_jpy': round(gross_jpy),
                    'tax_jpy': round(tax_jpy),
                    'net_amount_jpy': round(net_jpy),
                    'transaction_count': summary['transaction_count']
                })

def main():
    """メイン処理"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 初期化
        exchange_rate_manager = ExchangeRateManager()
        processor = TransactionProcessor(exchange_rate_manager)
        
        # JSONファイルの処理
        json_files = list(Path('.').glob('*.json'))
        if not json_files:
            logging.error("処理対象のJSONファイルが見つかりません")
            return
        
        # 取引データの読み込みと処理
        all_transactions = []
        for file in json_files:
            logging.info(f"ファイル {file} を処理中...")
            transactions = processor.load_transactions(file)
            all_transactions.extend(transactions)
        
        dividend_records = processor.process_transactions(all_transactions)
        
        # レポート出力
        detail_filename = 'dividend_tax_history.csv'
        summary_filename = 'dividend_tax_summary_by_symbol.csv'
        
        csv_writer = CSVReportWriter(detail_filename)
        csv_writer.write(dividend_records)
        
        symbol_writer = SymbolSummaryWriter(summary_filename)
        symbol_writer.write(dividend_records)
        
        console_writer = ConsoleReportWriter()
        console_writer.write(dividend_records)
        
        # 処理結果の表示
        logging.info(f"\n{len(json_files)}個のファイルから{len(dividend_records)}件のレコードを処理しました")
        logging.info(f"取引履歴は {detail_filename} に出力されました")
        logging.info(f"シンボル別集計は {summary_filename} に出力されました")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
