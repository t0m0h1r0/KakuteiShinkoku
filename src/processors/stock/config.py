from decimal import Decimal
from typing import Set


class StockProcessingConfig:
    """株式処理の設定と定数"""

    # 株式取引の有効なアクション
    STOCK_ACTIONS: Set[str] = {"BUY", "SELL"}

    # 売買の方向
    TRANSACTION_TYPES = {"BUY": "Buy", "SELL": "Sell"}

    # 取引単位（通常は1株）
    TRANSACTION_UNIT = Decimal("1")

    # デフォルトの手数料計算方法
    FEE_CALCULATION_METHOD = "per_transaction"

    # 株式取引の税金調整種別
    TAX_ADJUSTMENT_TYPES = {
        "REALIZED_GAIN": "Realized Gain/Loss",
        "WASH_SALE": "Wash Sale Rule",
    }
