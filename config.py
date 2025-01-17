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
DIVIDEND_HISTORY_FILE = f'{OUTPUT_DIR}/investment_income_history.csv'
DIVIDEND_SUMMARY_FILE = f'{OUTPUT_DIR}/investment_income_summary_by_symbol.csv'

# Transaction types
DIVIDEND_ACTIONS = {
    'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
    'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest',
    'CD Interest'  # CD利子も配当アクションに含める
}
TAX_ACTIONS = {'NRA Tax Adj', 'Pr Yr NRA Tax'}

# CD related constants
CD_MATURITY_ACTION = 'CD Deposit Funds'
CD_ADJUSTMENT_ACTION = 'CD Deposit Adj'
CD_INTEREST_ACTION = 'CD Interest'
CD_PURCHASE_KEYWORDS = ['CD FDIC INS']
CD_MATURED_KEYWORD = 'MATURED'

# Date parsing
CD_DATE_FORMAT = '%m/%d/%y'  # For parsing dates in CD descriptions