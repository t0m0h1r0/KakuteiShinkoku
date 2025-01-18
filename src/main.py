import sys
import logging
from pathlib import Path
import argparse
from datetime import datetime

from .config.settings import DATA_DIR
from .app.context import ApplicationContext
from .processors.data_processor import InvestmentDataProcessor
from .processors.report_generator import InvestmentReportGenerator

def parse_arguments():
    """コマンドライン引数のパース"""
    parser = argparse.ArgumentParser(description='Investment data processor')
    parser.add_argument(
        '--no-color',
        action='store_true',
        help='Disable colored output'
    )
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=DATA_DIR,
        help='Directory containing input files'
    )
    return parser.parse_args()

def setup_logging():
    """ログ設定"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    return logger

def main():
    """メインエントリーポイント"""
    start_time = datetime.now()
    args = parse_arguments()
    logger = setup_logging()

    try:
        # アプリケーションコンテキストの初期化
        context = ApplicationContext(use_color_output=not args.no_color)
        logger.info(f"Starting processing at {start_time}")

        # データ処理
        processor = InvestmentDataProcessor(context)
        if not processor.process_files(args.data_dir):
            logger.error("Data processing failed")
            return 1

        # レポート生成
        generator = InvestmentReportGenerator(context)
        generator.generate_report(context.processing_results)

        # 結果の表示
        context.display_results()

        # 実行時間の計算と表示
        end_time = datetime.now()
        execution_time = end_time - start_time
        logger.info(f"Processing completed in {execution_time}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        return 130  # 標準的なキーボード割り込み終了コード

    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        return 1

    finally:
        # コンテキストのクリーンアップ
        if 'context' in locals():
            context.cleanup()

if __name__ == "__main__":
    # パッケージのルートディレクトリをPythonパスに追加
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    sys.exit(main())