from pathlib import Path
import logging

from .processors.exchange_rate import ExchangeRateManager
from .processors.transaction import TransactionProcessor
from .writers.csv_report import CSVReportWriter
from .writers.console import ConsoleReportWriter
from .writers.symbol_summary import SymbolSummaryWriter

def main():
    """メイン処理"""
    try:
        # ロギングの設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 初期化
        exchange_rate_manager = ExchangeRateManager('data/HistoricalPrices.csv')
        processor = TransactionProcessor(exchange_rate_manager)
        
        # JSONファイルの処理
        json_files = list(Path('data/').glob('*.json'))
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
        
        # レポート出力の設定
        writers = [
            CSVReportWriter('output/dividend_tax_history.csv'),
            SymbolSummaryWriter('output/dividend_tax_summary_by_symbol.csv'),
            ConsoleReportWriter()
        ]
        
        # 各ライターでレポート出力
        for writer in writers:
            writer.write(dividend_records)
        
        # 処理結果の表示
        logging.info(f"\n{len(json_files)}個のファイルから{len(dividend_records)}件のレコードを処理しました")
        logging.info("取引履歴は dividend_tax_history.csv に出力されました")
        logging.info("シンボル別集計は dividend_tax_summary_by_symbol.csv に出力されました")
        
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()
