from typing import Set, FrozenSet

class ActionTypes:
    """取引アクションの定義クラス"""
    
    DIVIDEND_ACTIONS: FrozenSet[str] = frozenset({
        'Reinvest Dividend',
        'Cash Dividend',
        'Credit Interest',    
        'Bank Interest',
        'CD Interest',
        'QUALIFIED_DIVIDEND',
        'CASH_DIVIDEND',
        'REINVEST_DIVIDEND',
        'BOND_INTEREST'
    })

    TAX_ACTIONS: FrozenSet[str] = frozenset({
        'NRA Tax Adj',
        'PRIOR_YEAR_NRA_TAX',
        'Pr Yr NRA Tax',
        'Prior Year Tax'
    })

    OPTION_ACTIONS: FrozenSet[str] = frozenset({
        'SELL_TO_OPEN',
        'BUY_TO_OPEN',
        'BUY_TO_CLOSE',
        'SELL_TO_CLOSE',
        'EXPIRED',
        'ASSIGNED'
    })

    STOCK_ACTIONS: FrozenSet[str] = frozenset({
        'BUY',
        'SELL'
    })

    CD_ACTIONS: FrozenSet[str] = frozenset({
        'CD Deposit Funds',   
        'CD Maturity',        
        'CD Interest',        
        'CD Deposit Adj'      
    })

    @classmethod
    def is_dividend_action(cls, action: str) -> bool:
        """配当関連のアクションかどうかを判定"""
        return action.upper() in {a.upper() for a in cls.DIVIDEND_ACTIONS}

    @classmethod
    def is_tax_action(cls, action: str) -> bool:
        """税金関連のアクションかどうかを判定"""
        return action.upper() in {a.upper() for a in cls.TAX_ACTIONS}

    @classmethod
    def is_option_action(cls, action: str) -> bool:
        """オプション関連のアクションかどうかを判定"""
        return action.upper() in {a.upper() for a in cls.OPTION_ACTIONS}

    @classmethod
    def is_stock_action(cls, action: str) -> bool:
        """株式関連のアクションかどうかを判定"""
        return action.upper() in {a.upper() for a in cls.STOCK_ACTIONS}
