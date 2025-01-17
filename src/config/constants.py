# Transaction types
class TransactionType:
    STOCK = 'stock'
    OPTION = 'option'
    DIVIDEND = 'dividend'
    INTEREST = 'interest'
    CD_INTEREST = 'cd_interest'

# Income types
class IncomeType:
    DIVIDEND = 'Dividend'
    INTEREST = 'Interest'
    
# Option types
class OptionType:
    CALL = 'C'
    PUT = 'P'

# CD related constants
class CDConstants:
    MATURITY_ACTION = 'CD_MATURITY'
    ADJUSTMENT_ACTION = 'CD_ADJUSTMENT'
    INTEREST_ACTION = 'CD_INTEREST'
    PURCHASE_KEYWORDS = ['CD FDIC INS']
    MATURED_KEYWORD = 'MATURED'

# Currency codes
class Currency:
    USD = 'USD'
    JPY = 'JPY'

# Regular expressions
OPTION_SYMBOL_PATTERN = r"""
    ^(?P<underlying>[A-Z]+)\s+           # Underlying symbol
    (?P<expiry>\d{2}/\d{2}/\d{4})\s+    # Expiry date
    (?P<strike>\d+\.\d{2})\s+            # Strike price
    (?P<type>[CP])$                      # Option type (Call/Put)
"""
