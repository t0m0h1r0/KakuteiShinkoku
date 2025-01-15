from decimal import Decimal
from pathlib import Path

# Directory paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR / 'output'
EXCHANGE_RATES_DIR = DATA_DIR / 'exchange_rates'

# Exchange rate settings
DEFAULT_EXCHANGE_RATE = Decimal('150.0')
DATE_FORMAT = '%m/%d/%Y'

# File settings
CSV_ENCODING = 'utf-8'

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
EXCHANGE_RATES_DIR.mkdir(exist_ok=True)

# Transaction types
DIVIDEND_ACTIONS = {
    'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
    'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'
}
TAX_ACTIONS = {'NRA Tax Adj', 'Pr Yr NRA Tax'}
