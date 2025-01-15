from pathlib import Path
import logging

from src.config import DATA_DIR
from src.processors.exchange import ExchangeRateManager
from src.processors.transaction import TransactionProcessor
from src.writers.dividend import DividendReportWriter
from src.writers.console import ConsoleReportWriter
from src.writers.symbol import SymbolSummaryWriter

def main():
    """メイン処理"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 初期化
        exchange_rate_manager = ExchangeRateManager(DATA_DIR / 'HistoricalPrices.csv')
        processor = TransactionProcessor(exchange_rate_manager)
        
        # JSONファイルの処理
        json_files = list((DATA_DIR).glob('*.json'))
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
        
        dividend_writer = DividendReportWriter(detail_filename)
        dividend_writer.write(dividend_records)
        
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
