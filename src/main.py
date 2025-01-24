import sys
import logging
from pathlib import Path
import argparse
from datetime import datetime
from decimal import Decimal
import yaml
from typing import Dict, Any, List
import glob

from .app.application_context import ApplicationContext
from .app.data_processor import InvestmentDataProcessor
from .exchange.rate_provider import RateProvider

class Config:
    def __init__(self, config_path: Path):
        self.config = self._load_yaml(config_path)
        self._setup_paths()
    
    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _setup_paths(self):
        base_dir = Path(__file__).parent.parent
        
        self.config['data_dir'] = base_dir / self.config['data_dir']
        self.config['output_dir'] = base_dir / self.config['output_dir']
        self.config['exchange_rate_file'] = self.config['data_dir'] / self.config['exchange_rate_file']
        self.config['logging']['log_dir'] = base_dir / self.config['logging']['log_dir']
        
        self.config['data_dir'].mkdir(parents=True, exist_ok=True)
        self.config['output_dir'].mkdir(parents=True, exist_ok=True)
        self.config['logging']['log_dir'].mkdir(parents=True, exist_ok=True)

    def get_json_files(self) -> List[Path]:
        """設定されたパターンに基づいてJSONファイルを取得"""
        json_files = []
        data_dir = self.config['data_dir']
        
        # トランザクションファイルパターンの処理
        for pattern in self.config.get('transaction_files', ['*.json']):
            matched_files = list(data_dir.glob(pattern))
            json_files.extend(matched_files)
        
        return sorted(set(json_files))  # 重複を除去してソート
    
    def get_output_paths(self) -> Dict[str, Path]:
        return {
            key: self.config['output_dir'] / path 
            for key, path in self.config['output_files'].items()
        }
    
    def get_default_exchange_rate(self) -> Decimal:
        return Decimal(str(self.config['default_exchange_rate']))
    
    @property
    def data_dir(self) -> Path:
        return self.config['data_dir']
    
    @property
    def output_dir(self) -> Path:
        return self.config['output_dir']
    
    @property
    def exchange_rate_file(self) -> Path:
        return self.config['exchange_rate_file']
    
    @property
    def debug(self) -> bool:
        return self.config['debug']
    
    @property
    def use_color(self) -> bool:
        return self.config['use_color']
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        return self.config['logging']

def parse_arguments():
    parser = argparse.ArgumentParser(description='Investment data processor')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config.yaml'),
        help='Path to configuration file'
    )
    return parser.parse_args()

def main():
    start_time = datetime.now()
    args = parse_arguments()
    
    try:
        config = Config(args.config)
        context = ApplicationContext(config, use_color_output=config.use_color)
        logger = logging.getLogger(__name__)
        
        logger.info("Starting investment data processing...")
        RateProvider(config.exchange_rate_file)
        
        # JSONファイルの取得
        json_files = config.get_json_files()
        if not json_files:
            logger.error("No JSON files found matching the specified patterns")
            return 1
            
        logger.info(f"Found {len(json_files)} JSON files to process")
        
        processor = InvestmentDataProcessor(context)
        if not processor.process_files(json_files):
            logger.error("Data processing failed")
            return 1
        
        execution_time = datetime.now() - start_time
        logger.info(f"Processing completed in {execution_time}")
        return 0

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")
        return 1
    finally:
        if 'context' in locals():
            context.cleanup()

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))
    sys.exit(main())