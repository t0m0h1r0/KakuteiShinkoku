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
