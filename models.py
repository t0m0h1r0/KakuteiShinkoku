from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Transaction:
    """取引情報を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    amount: Decimal
    action: str

@dataclass(frozen=True)
class DividendRecord:
    """投資収入に関する記録を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    type: str
    gross_amount: Decimal
    tax: Decimal
    exchange_rate: Decimal
    reinvested: bool
    principal: Decimal = Decimal('0')  # CD元本用

    @property
    def net_amount_usd(self) -> Decimal:
        """米ドルでの手取り額を計算"""
        return round(self.gross_amount - self.tax, 2)

    @property
    def net_amount_jpy(self) -> Decimal:
        """日本円での手取り額を計算"""
        return round((self.gross_amount - self.tax) * self.exchange_rate)
        
    @property
    def gross_amount_jpy(self) -> Decimal:
        """日本円での総額を計算"""
        return round(self.gross_amount * self.exchange_rate)

    @property
    def tax_jpy(self) -> Decimal:
        """日本円での税額を計算"""
        return round(self.tax * self.exchange_rate)