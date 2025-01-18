from pathlib import Path
from typing import List, Dict, Any
import logging
from abc import ABC, abstractmethod

from ..core.types.transaction import Transaction
from ..app.context import ApplicationContext

class DataProcessor(ABC):
    """データ処理の基本クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def process_data(self, data: Any) -> Dict:
        """データ処理の抽象メソッド"""
        pass

class InvestmentDataProcessor(DataProcessor):
    """投資データ処理クラス"""
    
    def process_files(self, data_dir: Path) -> bool:
        """ファイル処理のメインフロー"""
        try:
            # JSONファイルの検索
            json_files = list(data_dir.glob('*.json'))
            if not json_files:
                self.logger.error("No JSON files found for processing")
                return False

            # トランザクションの処理
            all_transactions = self._load_transactions(json_files)
            if not all_transactions:
                return False

            # データの処理と結果の返却
            return self.process_data(all_transactions)

        except Exception as e:
            self.logger.error(f"Processing error: {e}", exc_info=True)
            return False

    def process_data(self, transactions: List[Transaction]) -> bool:
        """トランザクションデータの処理"""
        try:
            # レコードの生成
            dividend_records = self.context.dividend_processor.process_all(transactions)
            trade_records = self.context.trade_processor.process_all(transactions)

            # 結果をコンテキストに保存
            self.context.processing_results = {
                'dividend_records': dividend_records,
                'trade_records': trade_records
            }

            return True

        except Exception as e:
            self.logger.error(f"Data processing error: {e}", exc_info=True)
            return False

    def _load_transactions(self, json_files: List[Path]) -> List[Transaction]:
        """トランザクションの読み込み"""
        all_transactions = []
        for file in json_files:
            self.logger.info(f"Processing file: {file}")
            transactions = self.context.transaction_loader.load(file)
            all_transactions.extend(transactions)
        return all_transactions