from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

@dataclass(frozen=True)
class Transaction:
    """取引情報を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    amount: Decimal
    action: str
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    fees: Optional[Decimal] = None

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
    principal: Decimal = Decimal('0')

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

@dataclass(frozen=True)
class Position:
    """ポジション情報を表すデータクラス"""
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    
    @property
    def average_cost(self) -> Decimal:
        """平均取得単価を計算"""
        return round(self.cost_basis / self.quantity, 4) if self.quantity else Decimal('0')

@dataclass(frozen=True)
class TradeRecord:
    """取引損益に関する記録を表すイミュータブルなデータクラス"""
    date: str
    account: str
    symbol: str
    description: str
    type: str  # 'Stock' or 'Option'
    action: str
    quantity: Decimal
    price: Decimal
    fees: Decimal
    realized_gain: Decimal
    cost_basis: Decimal
    proceeds: Decimal
    exchange_rate: Decimal
    holding_period: Optional[int] = None  # 保有期間（日数）
    
    @property
    def realized_gain_jpy(self) -> Decimal:
        """日本円での実現損益を計算"""
        return round(self.realized_gain * self.exchange_rate)

    @property
    def cost_basis_jpy(self) -> Decimal:
        """日本円での取得価額を計算"""
        return round(self.cost_basis * self.exchange_rate)

    @property
    def proceeds_jpy(self) -> Decimal:
        """日本円での手取り額を計算"""
        return round(self.proceeds * self.exchange_rate)

@dataclass(frozen=True)
class OptionContract:
    """オプション契約情報を表すデータクラス"""
    underlying: str  # 原資産のシンボル
    expiry: str     # 満期日
    strike: Decimal # 権利行使価格
    type: str      # 'C' for Call, 'P' for Put
    
    @property
    def full_symbol(self) -> str:
        """完全なオプションシンボルを生成"""
        return f"{self.underlying} {self.expiry} {self.strike} {self.type}"