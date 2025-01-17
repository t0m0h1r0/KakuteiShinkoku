from typing import Set, FrozenSet

class ActionTypes:
    """取引アクションの定義クラス"""
    
    # Dividend related actions
    DIVIDEND_ACTIONS: FrozenSet[str] = frozenset({
        'QUALIFIED_DIVIDEND',
        'CASH_DIVIDEND',
        'REINVEST_DIVIDEND',
        'Credit Interest',    # 修正
        'BOND_INTEREST',
        'PRIOR_YEAR_DIVIDEND',
        'Bank Interest',      # 修正
        'CD Interest'         # 修正
    })

    # Tax related actions
    TAX_ACTIONS: FrozenSet[str] = frozenset({
        'NRA Tax Adj',       # 修正
        'PRIOR_YEAR_NRA_TAX'
    })

    # Option related actions
    OPTION_ACTIONS: FrozenSet[str] = frozenset({
        'SELL_TO_OPEN',
        'BUY_TO_OPEN',
        'BUY_TO_CLOSE',
        'SELL_TO_CLOSE',
        'EXPIRED',
        'ASSIGNED'
    })

    # Stock related actions
    STOCK_ACTIONS: FrozenSet[str] = frozenset({
        'BUY',
        'SELL'
    })

    # CD related actions
    CD_ACTIONS: FrozenSet[str] = frozenset({
        'CD Deposit Funds',   # 修正
        'CD Maturity',        # 修正
        'CD Interest',        # 修正
        'CD Deposit Adj'      # 修正
    })

    @classmethod
    def is_opening_action(cls, action: str) -> bool:
        """アクションが新規建てかどうかを判定"""
        return action in {'BUY', 'BUY_TO_OPEN', 'SELL_TO_OPEN'}

    @classmethod
    def is_closing_action(cls, action: str) -> bool:
        """アクションが決済かどうかを判定"""
        return action in {'SELL', 'BUY_TO_CLOSE', 'SELL_TO_CLOSE', 'EXPIRED', 'ASSIGNED'}

    @classmethod
    def is_dividend_action(cls, action: str) -> bool:
        """アクションが配当関連かどうかを判定"""
        return action in cls.DIVIDEND_ACTIONS

    @classmethod
    def is_tax_action(cls, action: str) -> bool:
        """アクションが税金関連かどうかを判定"""
        return action in cls.TAX_ACTIONS