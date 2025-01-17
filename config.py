from decimal import Decimal

# File related constants
CSV_ENCODING = 'utf-8'
DEFAULT_EXCHANGE_RATE = Decimal('150.0')
DATE_FORMAT = '%m/%d/%Y'

# Path constants
EXCHANGE_RATE_FILE = 'data/HistoricalPrices.csv'
OUTPUT_DIR = 'output'
DATA_DIR = 'data'

# Output file names
DIVIDEND_HISTORY_FILE = f'{OUTPUT_DIR}/dividend_tax_history.csv'
DIVIDEND_SUMMARY_FILE = f'{OUTPUT_DIR}/dividend_tax_summary_by_symbol.csv'

# Transaction types
DIVIDEND_ACTIONS = {
    'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
    'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'
}
TAX_ACTIONS = {'NRA Tax Adj', 'Pr Yr NRA Tax'}
