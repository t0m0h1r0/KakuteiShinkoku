from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional

@dataclass
class StockLot:
    """株式ロット（購入単位）を表すクラス"""
    quantity: Decimal
    price: Decimal
    fees: Decimal = Decimal('0')
    
    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.price, (int, float)):
            self.price = Decimal(str(self.price))
        if isinstance(self.fees, (int, float)):
            self.fees = Decimal(str(self.fees))

class StockPosition:
    """株式ポジション管理クラス"""
    def __init__(self):
        self.lots: List[StockLot] = []
    
    def add_lot(self, lot: StockLot) -> None:
        """ロットを追加"""
        self.lots.append(lot)

    def remove_shares(self, quantity: Decimal, price: Decimal, fees: Decimal) -> Decimal:
        """FIFOで株式を売却し、損益を計算"""
        if not self.lots:
            return Decimal('0')
        
        remaining_quantity = quantity
        realized_gain = Decimal('0')
        
        while remaining_quantity > 0 and self.lots:
            lot = self.lots[0]
            sell_quantity = min(remaining_quantity, lot.quantity)
            
            # 売却分の損益を計算
            # (売却価格 - 取得価格) * 数量
            trade_gain = (price - lot.price) * sell_quantity - fees * (sell_quantity / quantity)
            realized_gain += trade_gain
            
            if sell_quantity == lot.quantity:
                self.lots.pop(0)
            else:
                lot.quantity -= sell_quantity
                lot.fees = lot.fees * (lot.quantity / (lot.quantity + sell_quantity))
            
            remaining_quantity -= sell_quantity
        
        return realized_gain.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    @property
    def average_price(self) -> Decimal:
        total_cost = sum(lot.quantity * lot.price for lot in self.lots)
        total_quantity = sum(lot.quantity for lot in self.lots)
        return total_cost / total_quantity if total_quantity > 0 else Decimal('0')
    
    @property
    def total_quantity(self) -> Decimal:
        return sum(lot.quantity for lot in self.lots)