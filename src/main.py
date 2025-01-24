# main.py
import sys
import logging
from pathlib import Path
import argparse
from datetime import datetime
from decimal import Decimal
import yaml
from typing import Dict, Any, List

from .app.application_context import ApplicationContext
from .app.data_processor import InvestmentDataProcessor
from .exchange.rate_provider import RateProvider, ExchangePair
from .exchange.currency import Currency

class Config:
    def __init__(self, config_path: Path):
        self.config = self._load_yaml(config_path)
    
    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def get_json_files(self) -> List[Path]:
        return [Path(pattern) for pattern in self.config.get('transaction_files', [])]
    
    def get_output_paths(self) -> Dict[str, Path]:
        return {key: Path(path) for key, path in self.config['output_files'].items()}

    @property
    def debug(self) -> bool:
        return self.config['debug']
    
    @property
    def use_color(self) -> bool:
        return self.config['use_color']
    
    @property
    def logging_config(self) -> Dict[str, Any]:
        return self.config['logging']

    @property
    def exchange_config(self) -> Dict[str, Any]:
        return self.config['exchange']

def initialize_rate_provider(config: Config) -> None:
    rate_provider = RateProvider()
    pairs = []
    
    for pair_config in config.exchange_config['pairs']:
        base = Currency.from_str(pair_config['base'])
        target = Currency.from_str(pair_config['target'])
        default_rate = Decimal(str(pair_config['default_rate']))
        history_file = Path(pair_config['history_file']) if 'history_file' in pair_config else None
        
        pair = ExchangePair(base, target, default_rate, history_file)
        pairs.append(pair)
    
    rate_provider.initialize(pairs)

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
        
        # 為替レートプロバイダーの初期化
        initialize_rate_provider(config)
        
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
    sys.exit(main())