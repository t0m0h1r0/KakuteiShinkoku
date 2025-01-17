from pathlib import Path
import logging

from config import (
    EXCHANGE_RATE_FILE, DATA_DIR, 
    DIVIDEND_HISTORY_FILE, DIVIDEND_SUMMARY_FILE
)
from exchange_rates import ExchangeRateManager
from processors import TransactionProcessor
from writers import CSVReportWriter, ConsoleReportWriter, SymbolSummaryWriter

def main():
    """メイン処理"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 初期化
        exchange_rate_manager = ExchangeRateManager(EXCHANGE_RATE_FILE)
        processor = TransactionProcessor(exchange_rate_manager)
        
        # JSONファイルの処理
        json_files = list(Path(DATA_DIR).glob('*.json'))
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
        csv_writer = CSVReportWriter(DIVIDEND_HISTORY_FILE)
        csv_writer.write(dividend_records)
        
        symbol_writer = SymbolSummaryWriter(DIVIDEND_SUMMARY_FILE)
        symbol_writer.write(dividend_records)
        
        console_writer = ConsoleReportWriter()
        console_writer.write(dividend_records)
        
        # 処理結果の表示
        logging.info(f"\n{len(json_files)}個のファイルから{len(dividend_records)}件のレコードを処理しました")
        logging.info(f"取引履歴は {DIVIDEND_HISTORY_FILE} に出力されました")
        logging.info(f"シンボル別集計は {DIVIDEND_SUMMARY_FILE} に出力されました")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()
