from decimal import Decimal
import logging.config
from pathlib import Path
from typing import List, Optional
import sys

from src.config.settings import (
    DATA_DIR, OUTPUT_DIR, LOG_DIR,
    EXCHANGE_RATE_FILE, OUTPUT_FILES,
    LOGGING_CONFIG
)
from src.core.models import Transaction, DividendRecord, TradeRecord
from src.utils.exchange_rates import ExchangeRateProvider, ExchangeRateCache
from src.processors.transaction_loader import JSONTransactionLoader
from src.processors.dividend import DividendProcessor
from src.processors.cd import CDProcessor
from src.processors.trade import TradeProcessor, PositionManager
from src.writers.csv import (
    DividendHistoryWriter, TradeHistoryWriter,
    DividendSummaryWriter, OptionPremiumWriter
)
from src.writers.console import PrettyConsoleWriter

class ApplicationContext:
    """アプリケーションのコンテキスト管理クラス"""
    
    def __init__(self):
        # 初期設定
        self._setup_directories()
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # コンポーネントの初期化
        self.exchange_rate_provider = self._create_exchange_rate_provider()
        self.position_manager = PositionManager()
        self.transaction_loader = JSONTransactionLoader()

        # プロセッサーの初期化
        self.dividend_processor = DividendProcessor(self.exchange_rate_provider)
        self.cd_processor = CDProcessor(self.exchange_rate_provider)
        self.trade_processor = TradeProcessor(
            self.exchange_rate_provider,
            self.position_manager
        )
        
        # ライターの初期化
        self.writers = self._setup_writers()

    @staticmethod
    def _setup_logging():
        """ログ設定"""
        logging.config.dictConfig(LOGGING_CONFIG)

    @staticmethod
    def _setup_directories():
        """ディレクトリ構造の設定"""
        if not DATA_DIR.exists():
            raise FileNotFoundError(
                f"Data directory not found: {DATA_DIR}. "
                "Please create the directory and add required data files."
            )

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        if not EXCHANGE_RATE_FILE.exists():
            raise FileNotFoundError(
                f"Exchange rate file not found: {EXCHANGE_RATE_FILE}. "
                "Please add the required file."
            )

    def _create_exchange_rate_provider(self) -> ExchangeRateProvider:
        """為替レートプロバイダーの作成"""
        provider = ExchangeRateProvider(EXCHANGE_RATE_FILE)
        return ExchangeRateCache(provider)

    def _setup_writers(self) -> dict:
        """ライターの設定"""
        return {
            'dividend_history': DividendHistoryWriter(
                OUTPUT_FILES['dividend_history']
            ),
            'dividend_summary': DividendSummaryWriter(
                OUTPUT_FILES['dividend_summary']
            ),
            'trade_history': TradeHistoryWriter(
                OUTPUT_FILES['trade_history']
            ),
            'option_premium': OptionPremiumWriter(  # 新規追加
                OUTPUT_FILES['option_premium']
            ),
            'console': PrettyConsoleWriter()
        }

class InvestmentDataProcessor:
    """投資データ処理の主制御クラス"""
    
    def __init__(self, context: ApplicationContext):
        self.context = context
        self.logger = logging.getLogger(__name__)

    def process_files(self) -> bool:
        """ファイル処理のメインフロー"""
        try:
            # JSONファイルの検索
            json_files = list(DATA_DIR.glob('*.json'))
            if not json_files:
                self.logger.error("No JSON files found for processing")
                return False

            # トランザクションの処理
            all_transactions = self._process_transactions(json_files)
            if not all_transactions:
                return False

            # 各種記録の生成
            dividend_records = self._generate_dividend_records(all_transactions)
            cd_records = self._generate_cd_records(all_transactions)
            trade_records = self._generate_trade_records(all_transactions)

            # レポート出力
            self._write_reports(dividend_records, cd_records, trade_records)
            
            # オプションプレミアムレポートの出力
            self._write_option_premium_report()
            
            # 処理結果のサマリー表示
            self._display_processing_summary(
                len(json_files),
                len(dividend_records),
                len(cd_records),
                len(trade_records)
            )
            
            return True

        except Exception as e:
            self.logger.error(f"Processing error: {e}", exc_info=True)
            return False

    def _process_transactions(self, json_files: List[Path]) -> Optional[List[Transaction]]:
        """トランザクションの処理"""
        try:
            all_transactions = []
            for file in json_files:
                self.logger.info(f"Processing file: {file}")
                transactions = self.context.transaction_loader.load(str(file))
                all_transactions.extend(transactions)
            return all_transactions
        except Exception as e:
            self.logger.error(f"Transaction processing error: {e}", exc_info=True)
            return None

    def _generate_dividend_records(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """配当記録の生成"""
        return self.context.dividend_processor.process_all(transactions)

    def _generate_cd_records(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """CD記録の生成"""
        for trans in transactions:
            self.context.cd_processor.process(trans)
        return self.context.cd_processor.get_records()

    def _generate_trade_records(self, transactions: List[Transaction]) -> List[TradeRecord]:
        """取引記録の生成"""
        for trans in transactions:
            self.context.trade_processor.process(trans)
        return self.context.trade_processor.get_records()

    def _write_reports(self, dividend_records: List[DividendRecord],
                      cd_records: List[DividendRecord],
                      trade_records: List[TradeRecord]) -> None:
        """レポートの出力"""
        # 全ての収入記録を結合
        all_income_records = dividend_records + cd_records

        # 各種レポートの出力
        self.context.writers['dividend_history'].write(all_income_records)
        self.context.writers['dividend_summary'].write(all_income_records)
        self.context.writers['trade_history'].write(trade_records)
        self.context.writers['console'].write(all_income_records)

    def _write_option_premium_report(self) -> None:
        """オプションプレミアムレポートの出力"""
        # プレミアム記録の取得
        premium_records = self.context.trade_processor.get_option_premium_records()
        if premium_records:
            # プレミアム取引の詳細を出力
            self.context.writers['option_premium'].write(premium_records)
            
            # サマリー情報を出力
            summary = self.context.trade_processor.get_option_premium_summary()
            self.context.writers['option_premium'].write_summary(summary)
            
            self.logger.info(
                f"Option premium report generated with {len(premium_records)} records"
            )

    def _display_processing_summary(self, file_count: int,
                                 dividend_count: int,
                                 cd_count: int,
                                 trade_count: int) -> None:
        """処理結果のサマリー表示"""
        self.logger.info(f"\nProcessing Summary:")
        self.logger.info(f"- Files processed: {file_count}")
        self.logger.info(f"- Dividend records: {dividend_count}")
        self.logger.info(f"- CD interest records: {cd_count}")
        self.logger.info(f"- Trade records: {trade_count}")
        
        # オプションプレミアムのサマリーを追加
        option_summary = self.context.trade_processor.get_option_premium_summary()
        if option_summary['transaction_count'] > 0:
            self.logger.info(
                f"- Option premium records: {option_summary['transaction_count']}"
            )
            self.logger.info(
                f"- Total net premium: ${option_summary['net_premium']:.2f}"
            )
        
        self.logger.info(f"Output files generated in: {OUTPUT_DIR}")

def main():
    """メインエントリーポイント"""
    try:
        # アプリケーションコンテキストの初期化
        context = ApplicationContext()
        
        # プロセッサーの作成と実行
        processor = InvestmentDataProcessor(context)
        success = processor.process_files()
        
        # 終了コードの設定
        sys.exit(0 if success else 1)
    
    except Exception as e:
        logging.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()