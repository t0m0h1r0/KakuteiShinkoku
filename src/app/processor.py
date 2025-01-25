from typing import List, Dict, Any
import logging
from pathlib import Path
import traceback

from ..core.transaction import Transaction
from .reporter import InvestmentReporter

class InvestmentProcessor:
    """投資データ処理クラス"""
    
    def __init__(self, context):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)
        self.reporter = InvestmentReporter(self.context.writers)

    def process_files(self, json_files: List[Path]) -> bool:
        """複数のJSONファイルを処理"""
        try:
            transactions = self._load_transactions(json_files)
            if not transactions:
                self.logger.error("トランザクションの読み込みに失敗")
                return False

            return self.process_data(transactions)

        except Exception as e:
            self.logger.error(f"処理エラー: {e}\n{traceback.format_exc()}")
            return False

    def process_data(self, transactions: List[Transaction]) -> bool:
        """トランザクションデータの処理"""
        try:
            sorted_transactions = sorted(transactions, key=lambda x: x.transaction_date)
            
            processing_results = self._process_transactions(sorted_transactions)
            if not processing_results:
                return False

            self.context.processing_results = processing_results
            return self.reporter.generate_reports(processing_results)

        except Exception as e:
            self.logger.error(f"データ処理エラー: {e}\n{traceback.format_exc()}")
            return False

    def _load_transactions(self, json_files: List[Path]) -> List[Transaction]:
        """トランザクションの読み込み"""
        all_transactions = []
        
        for file in json_files:
            try:
                self.logger.info(f"ファイル処理中: {file}")
                transactions = self.context.transaction_loader.load(file)
                all_transactions.extend(transactions)
                self.logger.debug(f"{file}から{len(transactions)}件のトランザクションを読み込み")
            except Exception as e:
                self.logger.error(f"ファイル{file}の処理エラー: {e}\n{traceback.format_exc()}")
                continue

        return all_transactions

    def _process_transactions(self, transactions: List[Transaction]) -> Dict[str, Any]:
        """各種トランザクションの処理"""
        try:
            dividend_records = self.context.dividend_processor.process_all(transactions)
            interest_records = self.context.interest_processor.process_all(transactions)
            stock_records = self.context.stock_processor.process_all(transactions)
            option_records = self.context.option_processor.process_all(transactions)

            total_records = (
                len(dividend_records) +
                len(interest_records) +
                len(stock_records) +
                len(option_records)
            )
            self.logger.info(f"合計{total_records}件のレコードを処理")

            return {
                'dividend_records': dividend_records,
                'interest_records': interest_records,
                'stock_records': stock_records,
                'option_records': option_records,
                'option_processor': self.context.option_processor
            }

        except Exception as e:
            self.logger.error(f"トランザクション処理エラー: {e}")
            return None