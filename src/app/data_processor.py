from typing import List, Dict, Any
import logging
import traceback
from pathlib import Path

from ..core.transaction import Transaction
from ..app.application_context import ApplicationContext
from ..report.manager import InvestmentReportManager

class DataProcessor:
    """データ処理の基本クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

class InvestmentDataProcessor(DataProcessor):
    """投資データ処理クラス"""
    
    def process_files(self, json_files: List[Path]) -> bool:
        """複数のJSONファイルを処理"""
        try:
            all_transactions = []
            
            # 各JSONファイルからトランザクションを読み込み
            for file in json_files:
                try:
                    self.logger.info(f"Processing file: {file}")
                    transactions = self.context.transaction_loader.load(file)
                    all_transactions.extend(transactions)
                    self.logger.debug(f"Successfully loaded {len(transactions)} transactions from {file}")
                except Exception as e:
                    self.logger.error(f"Error processing file {file}: {e}\n{traceback.format_exc()}")
                    continue

            if not all_transactions:
                self.logger.error("No transactions were loaded from any files")
                return False

            # データの処理と結果の返却
            return self.process_data(all_transactions)

        except Exception as e:
            self.logger.error(f"Processing error: {e}\n{traceback.format_exc()}")
            return False

    def process_data(self, transactions: List[Transaction]) -> bool:
        """トランザクションデータの処理"""
        try:
            # トランザクションを日付順にソート
            self.logger.debug("Sorting transactions by date...")
            sorted_transactions = sorted(transactions, key=lambda x: x.transaction_date)
            
            # 各プロセッサで処理
            self.logger.debug("Processing dividend records...")
            dividend_records = self.context.dividend_processor.process_all(sorted_transactions)
            
            self.logger.debug("Processing interest records...")
            interest_records = self.context.interest_processor.process_all(sorted_transactions)
            
            self.logger.debug("Processing stock records...")
            stock_records = self.context.stock_processor.process_all(sorted_transactions)
            
            self.logger.debug("Processing option records...")
            option_records = self.context.option_processor.process_all(sorted_transactions)

            # 結果をコンテキストに保存
            self.logger.debug("Saving results to context...")
            self.context.processing_results = {
                'dividend_records': dividend_records,
                'interest_records': interest_records,
                'stock_records': stock_records,
                'option_records': option_records,
                'option_processor': self.context.option_processor
            }

            # レポート生成
            report_manager = InvestmentReportManager(self.context.writers)
            report_manager.generate_reports(self.context.processing_results)

            # 処理されたトランザクション数をログ出力
            total_records = (
                len(dividend_records) +
                len(interest_records) +
                len(stock_records) +
                len(option_records)
            )
            self.logger.info(f"Successfully processed {total_records} total records")

            return True

        except Exception as e:
            self.logger.error(f"Data processing error: {e}\n{traceback.format_exc()}")
            return False