from typing import Set


class DividendActionTypes:
    VALID_ACTIONS: Set[str] = {
        "DIVIDEND",
        "CASH DIVIDEND",
        "REINVEST DIVIDEND",
        "REINVEST SHARES",
        "PR YR CASH DIV",
    }

    TAX_ACTIONS: Set[str] = {"NRA TAX ADJ", "PR YR NRA TAX"}


class DividendTypes:
    CASH = "Cash Dividend"
    REINVESTED = "Reinvested Dividend"
    QUALIFIED = "Qualified Dividend"
    NON_QUALIFIED = "Non-Qualified Dividend"
