from pathlib import Path
import logging

from config import (
    EXCHANGE_RATE_FILE, DATA_DIR, OUTPUT_DIR,
    DIVIDEND_HISTORY_FILE, DIVIDEND_SUMMARY_FILE,
    TRADING_HISTORY_FILE, TRADING_SUMMARY_FILE
)
from exchange_rates import ExchangeRateManager
from processors import TransactionProcessor, CDProcessor, TradeProcessor
from writers import (
    CSVReportWriter, ConsoleReportWriter,
    SymbolSummaryWriter, TradeReportWriter
)

def main():
    """メイン処理"""
    try:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 出力ディレクトリの作成
        Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
        
        # 初期化
        exchange_rate_manager = ExchangeRateManager(EXCHANGE_RATE_FILE)
        dividend_processor = TransactionProcessor(exchange_rate_manager)
        cd_processor = CDProcessor(exchange_rate_manager)
        trade_processor = TradeProcessor(exchange_rate_manager)
        
        # JSONファイルの処理
        json_files = list(Path(DATA_DIR).glob('*.json'))
        if not json_files:
            logging.error("処理対象のJSONファイルが見つかりません")
            return
        
        # 取引データの読み込みと処理
        all_transactions = []
        for file in json_files:
            logging.info(f"ファイル {file} を処理中...")
            transactions = dividend_processor.load_transactions(file)
            all_transactions.extend(transactions)
        
        # 配当情報の処理
        dividend_records = dividend_processor.process_transactions(all_transactions)
        
        # CD情報の処理
        for trans in all_transactions:
            cd_processor.process_transaction(trans)
        cd_interest_records = cd_processor.get_interest_records()
        
        # 取引情報の処理
        for trans in all_transactions:
            trade_processor.process_transaction(trans)
        trade_records = trade_processor.get_trade_records()
        
        # 全ての収入記録を結合
        all_income_records = dividend_records + cd_interest_records
        
        # レポート出力 - 配当・利子
                # レポート出力 - 配当・利子
        csv_writer = CSVReportWriter(DIVIDEND_HISTORY_FILE)
        csv_writer.write(all_income_records)
        
        symbol_writer = SymbolSummaryWriter(DIVIDEND_SUMMARY_FILE)
        symbol_writer.write(all_income_records)
        
        console_writer = ConsoleReportWriter()
        console_writer.write(all_income_records)
        
        # レポート出力 - 取引損益
        trade_writer = TradeReportWriter(TRADING_HISTORY_FILE, TRADING_SUMMARY_FILE)
        trade_writer.write(trade_records)
        
        # 処理結果の表示
        logging.info(f"\n{len(json_files)}個のファイルから処理したレコード:")
        logging.info(f"- 配当・利子: {len(dividend_records)}件")
        logging.info(f"- CD利子: {len(cd_interest_records)}件")
        logging.info(f"- 取引: {len(trade_records)}件")
        logging.info(f"投資収入履歴は {DIVIDEND_HISTORY_FILE} に出力されました")
        logging.info(f"投資収入集計は {DIVIDEND_SUMMARY_FILE} に出力されました")
        logging.info(f"取引履歴は {TRADING_HISTORY_FILE} に出力されました")
        logging.info(f"取引集計は {TRADING_SUMMARY_FILE} に出力されました")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")

if __name__ == "__main__":
    main()