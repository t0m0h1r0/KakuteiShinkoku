import sys
import logging
from pathlib import Path
import argparse
from datetime import datetime

from .config.settings import DATA_DIR
from .app.application_context import ApplicationContext
from .app.data_processor import InvestmentDataProcessor
from .app.report_generator import InvestmentReportGenerator

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
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )
    return parser.parse_args()

def setup_logging(debug_mode: bool = False):
    """ログ設定"""
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
    return logger

def main():
    """メインエントリーポイント"""
    start_time = datetime.now()
    args = parse_arguments()
    logger = setup_logging(args.debug)

    try:
        logger.info("Starting investment data processing...")
        
        # アプリケーションコンテキストの初期化
        logger.debug("Initializing application context...")
        context = ApplicationContext(use_color_output=not args.no_color)
        logger.info(f"Starting processing at {start_time}")

        # データ処理
        logger.debug("Creating data processor...")
        processor = InvestmentDataProcessor(context)
        
        logger.info(f"Processing files from directory: {args.data_dir}")
        if not processor.process_files(args.data_dir):
            logger.error("Data processing failed")
            return 1
        
        logger.info("Data processing completed successfully")

        # レポート生成
        logger.debug("Creating report generator...")
        generator = InvestmentReportGenerator(context)
        
        logger.info("Generating reports...")
        generator.generate_report(context.processing_results)

        # 結果の表示
        logger.debug("Displaying results...")
        context.display_results()

        # 実行時間の計算と表示
        end_time = datetime.now()
        execution_time = end_time - start_time
        logger.info(f"Processing completed in {execution_time}")

        return 0

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        return 1

    finally:
        # コンテキストのクリーンアップ
        if 'context' in locals():
            logger.debug("Cleaning up context...")
            context.cleanup()

if __name__ == "__main__":
    # パッケージのルートディレクトリをPythonパスに追加
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    sys.exit(main())