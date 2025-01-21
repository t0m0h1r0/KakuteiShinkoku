from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional

@dataclass
class StockLot:
    """株式ロット（購入単位）を表すクラス"""
    trade_date: date
    quantity: Decimal
    price: Decimal
    fees: Decimal
    
    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.price, (int, float)):
            self.price = Decimal(str(self.price))
        if isinstance(self.fees, (int, float)):
            self.fees = Decimal(str(self.fees))

@dataclass
class ClosedTrade:
    """決済済み取引情報"""
    open_date: date
    close_date: date
    quantity: Decimal
    open_price: Decimal
    close_price: Decimal
    open_fees: Decimal
    close_fees: Decimal
    realized_gain: Decimal

    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.open_price, (int, float)):
            self.open_price = Decimal(str(self.open_price))
        if isinstance(self.close_price, (int, float)):
            self.close_price = Decimal(str(self.close_price))
        if isinstance(self.open_fees, (int, float)):
            self.open_fees = Decimal(str(self.open_fees))
        if isinstance(self.close_fees, (int, float)):
            self.close_fees = Decimal(str(self.close_fees))
        if isinstance(self.realized_gain, (int, float)):
            self.realized_gain = Decimal(str(self.realized_gain))

class StockPosition:
    """株式ポジション管理クラス"""
    def __init__(self):
        self.lots: List[StockLot] = []
        self.closed_trades: List[ClosedTrade] = []
    
    def add_lot(self, lot: StockLot) -> None:
        """ロットを追加"""
        self.lots.append(lot)
    
    def sell_shares(self, quantity: Decimal, price: Decimal, fees: Decimal) -> Decimal:
        """FIFOで株式を売却し、損益を計算"""
        if not self.lots:
            return Decimal('0')
        
        remaining_quantity = quantity
        realized_gain = Decimal('0')
        
        while remaining_quantity > 0 and self.lots:
            lot = self.lots[0]
            if lot.quantity <= remaining_quantity:
                # ロット全体を売却
                sold_quantity = lot.quantity
                remaining_quantity -= lot.quantity
                self.lots.pop(0)
            else:
                # ロットの一部を売却
                sold_quantity = remaining_quantity
                lot.quantity -= remaining_quantity
                lot.fees = lot.fees * (lot.quantity - remaining_quantity) / lot.quantity
                remaining_quantity = Decimal('0')
            
            # 売却分の損益を計算
            trade_realized_gain = self._calculate_realized_gain(
                sold_quantity, lot.price, price,
                lot.fees * (sold_quantity / lot.quantity),
                fees * (sold_quantity / quantity)
            )
            realized_gain += trade_realized_gain
            
            # 決済済み取引を記録
            self.closed_trades.append(ClosedTrade(
                open_date=lot.trade_date,
                close_date=date.today(),  # 実際の取引日を渡す必要あり
                quantity=sold_quantity,
                open_price=lot.price,
                close_price=price,
                open_fees=lot.fees * (sold_quantity / lot.quantity),
                close_fees=fees * (sold_quantity / quantity),
                realized_gain=trade_realized_gain
            ))
        
        return realized_gain

    def get_position_summary(self) -> Dict:
        """ポジション情報を取得"""
        total_quantity = Decimal('0')
        total_cost = Decimal('0')
        total_fees = Decimal('0')
        
        for lot in self.lots:
            total_quantity += lot.quantity
            total_cost += lot.price * lot.quantity
            total_fees += lot.fees
        
        average_cost = (total_cost / total_quantity) if total_quantity > 0 else Decimal('0')
        
        return {
            'quantity': total_quantity,
            'average_cost': average_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_cost': total_cost.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_fees': total_fees.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'has_position': total_quantity > 0
        }

    def get_realized_gains(self) -> Dict[str, Decimal]:
        """実現損益の集計を取得"""
        total_realized_gain = Decimal('0')
        total_fees = Decimal('0')
        
        for trade in self.closed_trades:
            total_realized_gain += Decimal(str(trade.realized_gain))
            total_fees += Decimal(str(trade.open_fees)) + Decimal(str(trade.close_fees))
        
        return {
            'total_realized_gain': total_realized_gain.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_fees': total_fees.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

    @staticmethod
    def _calculate_realized_gain(quantity: Decimal, open_price: Decimal,
                               close_price: Decimal, open_fees: Decimal,
                               close_fees: Decimal) -> Decimal:
        """個別取引の損益計算"""
        cost_basis = quantity * open_price + open_fees
        proceeds = quantity * close_price - close_fees
        return (proceeds - cost_basis).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)