# Income types
class IncomeType:
    DIVIDEND = 'Dividend'
    INTEREST = 'Interest'
    CD_INTEREST = 'CD Interest'

# Option types
class OptionType:
    CALL = 'C'
    PUT = 'P'

# CD関連の定数
class CDConstants:
    MATURITY_ACTION = 'CD_MATURITY'
    ADJUSTMENT_ACTION = 'CD_ADJUSTMENT'
    INTEREST_ACTION = 'CD_INTEREST'
    PURCHASE_KEYWORDS = ['CD FDIC INS']
    MATURED_KEYWORD = 'MATURED'

# 正規表現パターン
OPTION_SYMBOL_PATTERN = r"""
    ^(?P<underlying>[A-Z]+)\s+           # 原資産シンボル
    (?P<expiry>\d{2}/\d{2}/\d{4})\s+    # 満期日
    (?P<strike>\d+\.\d{2})\s+            # 行使価格
    (?P<type>[CP])$                      # オプションタイプ（コール/プット）
"""

# トランザクション種別
class TransactionType:
    STOCK = 'stock'
    OPTION = 'option'
    DIVIDEND = 'dividend'
    INTEREST = 'interest'
    CD_INTEREST = 'cd_interest'
