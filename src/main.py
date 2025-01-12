# src/main.py
import logging
from pathlib import Path
from .processors.exchange_rate import ExchangeRateManager
from .processors.transaction import TransactionProcessor
from .writers.csv_detail import CSVReportWriter
from .writers.symbol_summary import SymbolSummaryWriter
from .writers.console import ConsoleReportWriter

def main():
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
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
        
        detail_filename = 'dividend_tax_history.csv'
        summary_filename = 'dividend_tax_summary_by_symbol.csv'
        
        csv_writer = CSVReportWriter(detail_filename)
        csv_writer.write(dividend_records)
        
        symbol_writer = SymbolSummaryWriter(summary_filename)
        symbol_writer.write(dividend_records)
        
        console_writer = ConsoleReportWriter()
        console_writer.write(dividend_records)
        
        logging.info(f"\n{len(json_files)}個のファイルから{len(dividend_records)}件のレコードを処理しました")
        logging.info(f"取引履歴は {detail_filename} に出力されました")
        logging.info(f"シンボル別集計は {summary_filename} に出力されました")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()

