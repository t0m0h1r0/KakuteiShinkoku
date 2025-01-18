from pathlib import Path
from decimal import Decimal

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
LOG_DIR = OUTPUT_DIR / 'logs'

# File settings
FILE_ENCODING = 'utf-8'

# Date formats
INPUT_DATE_FORMAT = '%m/%d/%Y'    # JSONファイルの日付形式
OUTPUT_DATE_FORMAT = '%Y-%m-%d'    # 出力ファイルの日付形式

# Exchange rate settings
DEFAULT_EXCHANGE_RATE = Decimal('150.0')

# Input files
EXCHANGE_RATE_FILE = DATA_DIR / 'HistoricalPrices.csv'

# Output files
OUTPUT_FILES = {
    'dividend_history': OUTPUT_DIR / 'dividend_history.csv',
    'dividend_summary': OUTPUT_DIR / 'dividend_summary.csv',
    'trade_history': OUTPUT_DIR / 'trade_history.csv',
    'trade_summary': OUTPUT_DIR / 'trade_summary.csv',
    'option_premium': OUTPUT_DIR / 'option_premium.csv',    # 追加：オプションプレミアム出力
    'option_summary': OUTPUT_DIR / 'option_premium_summary.txt'  # 追加：オプションサマリー出力
}

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'formatters': {
        'detailed': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': str(LOG_DIR / 'processing.log'),
            'formatter': 'detailed',
            'level': 'DEBUG'
        }
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'DEBUG'
    }
}

# Option Trading Constants
OPTION_TRADING_CONFIG = {
    'min_premium_threshold': Decimal('10.0'),  # 最小プレミアム閾値（USD）
    'max_loss_threshold': Decimal('1000.0'),   # 最大損失閾値（USD）
    'premium_calculation_method': 'NET',       # 'NET' or 'GROSS'
    'include_expired_options': True,           # 期限切れオプションを含めるか
    'include_assigned_options': True           # 権利行使されたオプションを含めるか
}