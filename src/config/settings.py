from pathlib import Path
from decimal import Decimal

# ベースパス
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
LOG_DIR = OUTPUT_DIR / 'logs'

# ファイル設定
FILE_ENCODING = 'utf-8'

# 日付形式
INPUT_DATE_FORMAT = '%m/%d/%Y'
OUTPUT_DATE_FORMAT = '%Y-%m-%d'

# 為替レート設定
DEFAULT_EXCHANGE_RATE = Decimal('150.0')

# 入力ファイル
EXCHANGE_RATE_FILE = DATA_DIR / 'HistoricalPrices.csv'

# 出力ファイル
OUTPUT_FILES = {
    'dividend_history': OUTPUT_DIR / 'dividend_history.csv',
    'dividend_summary': OUTPUT_DIR / 'dividend_summary.csv',
    'stock_trade_history': OUTPUT_DIR / 'stock_trade_history.csv',
    'option_trade_history': OUTPUT_DIR / 'option_trade_history.csv',
    'trade_summary': OUTPUT_DIR / 'trade_summary.csv',
    'option_premium': OUTPUT_DIR / 'option_premium.csv',
    'option_summary': OUTPUT_DIR / 'option_premium_summary.txt',
    'profit_loss_summary': OUTPUT_DIR / 'profit_loss_summary.csv',  # Ensuring CSV extension
    'detailed_profit_loss_summary': OUTPUT_DIR / 'detailed_profit_loss_summary.csv'
}

# ロギング設定
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

# オプション取引設定
OPTION_TRADING_CONFIG = {
    'min_premium_threshold': Decimal('10.0'),  # 最小プレミアム閾値
    'max_loss_threshold': Decimal('1000.0'),   # 最大損失閾値
    'premium_calculation_method': 'NET',       # プレミアム計算方法
    'include_expired_options': True,           # 期限切れオプションを含めるか
    'include_assigned_options': True           # 権利行使オプションを含めるか
}