# src/utils/constants.py
from decimal import Decimal

DEFAULT_EXCHANGE_RATE = Decimal('150.0')
DATE_FORMAT = '%m/%d/%Y'
CSV_ENCODING = 'utf-8'

DIVIDEND_ACTIONS = {
    'Qualified Dividend', 'Cash Dividend', 'Reinvest Dividend',
    'Credit Interest', 'Bond Interest', 'Pr Yr Cash Div', 'Bank Interest'
}
TAX_ACTIONS = {'NRA Tax Adj', 'Pr Yr NRA Tax'}

