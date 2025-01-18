import sys
from pathlib import Path

from .config.settings import DATA_DIR
from .app.context import ApplicationContext
from .app.processor import InvestmentDataProcessor

def main():
    """メインエントリーポイント"""
    try:
        # アプリケーションコンテキストの初期化
        context = ApplicationContext()
        
        # プロセッサーの作成と実行
        processor = InvestmentDataProcessor(context)
        success = processor.process_files(DATA_DIR)
        
        # 終了コードの設定
        sys.exit(0 if success else 1)
    
    except Exception as e:
        logging.error(f"Application error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
