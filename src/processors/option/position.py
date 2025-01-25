from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional
from .config import OptionProcessingConfig

@dataclass
class OptionContract:
    """オプション契約情報"""
    trade_date: date
    quantity: Decimal
    price: Decimal     # 1株あたりの価格
    fees: Decimal      # 取引手数料
    position_type: str # 'Long' or 'Short'
    option_type: str   # 'Call' or 'Put'

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
    position_type: str

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

class OptionPosition:
    """オプションポジション管理クラス"""
    
    def __init__(self):
        self.long_contracts: List[OptionContract] = []  # 買いポジション
        self.short_contracts: List[OptionContract] = [] # 売りポジション
        self.closed_trades: List[ClosedTrade] = []     # 決済済み取引
        
    def add_contract(self, contract: OptionContract) -> None:
        """契約を追加"""
        if contract.position_type == OptionProcessingConfig.POSITION_TYPES['LONG']:
            self.long_contracts.append(contract)
        else:
            self.short_contracts.append(contract)

    def close_position(self, 
                      close_date: date,
                      quantity: Decimal,
                      close_price: Decimal,
                      close_fees: Decimal,
                      is_buy: bool) -> Dict[str, Decimal]:
        """ポジションを決済"""
        if quantity <= 0:
            raise ValueError("数量は正の値である必要があります")
        
        # 決済対象のコントラクトを取得
        contracts = self.short_contracts if is_buy else self.long_contracts
        if not contracts:
            raise ValueError("決済可能なポジションがありません")
        
        # 決済に必要な数量が存在することを確認
        total_available = sum(c.quantity for c in contracts)
        if total_available < quantity:
            raise ValueError(f"決済に必要な数量が不足しています。必要: {quantity}, 利用可能: {total_available}")

        # 1契約あたりの手数料を計算
        fee_per_contract = close_fees / quantity
        realized_gain = Decimal('0')
        remaining_quantity = quantity
        
        while remaining_quantity > 0 and contracts:
            contract = contracts[0]
            close_quantity = min(remaining_quantity, contract.quantity)
            
            # 決済分の手数料を計算
            contract_close_fees = fee_per_contract * close_quantity
            contract_open_fees = contract.fees * (close_quantity / contract.quantity)
            
            # 損益を計算
            trade_pnl = self._calculate_pnl(
                contract.position_type,
                contract.price,
                close_price,
                contract_open_fees,
                contract_close_fees,
                close_quantity
            )
            realized_gain += trade_pnl
            
            # 決済情報を記録
            self.closed_trades.append(ClosedTrade(
                open_date=contract.trade_date,
                close_date=close_date,
                quantity=close_quantity,
                open_price=contract.price,
                close_price=close_price,
                open_fees=contract_open_fees,
                close_fees=contract_close_fees,
                realized_gain=trade_pnl,
                position_type=contract.position_type
            ))
            
            # 残数量を更新
            if close_quantity == contract.quantity:
                contracts.pop(0)
            else:
                contract.quantity -= close_quantity
                contract.fees = contract.fees * (contract.quantity / (contract.quantity + close_quantity))
            
            remaining_quantity -= close_quantity
        
        return {
            'realized_gain': realized_gain.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

    def handle_expiration(self, expire_date: date) -> Dict[str, Decimal]:
        """期限切れの処理"""
        premium_pnl = Decimal('0')
        
        # ロングポジションの処理（支払ったプレミアムは損失）
        for contract in self.long_contracts:
            contract_premium = (
                contract.price * 
                contract.quantity * 
                OptionProcessingConfig.SHARES_PER_CONTRACT
            )
            premium_pnl -= (contract_premium + contract.fees)
            
        # ショートポジションの処理（受け取ったプレミアムは利益）
        for contract in self.short_contracts:
            contract_premium = (
                contract.price * 
                contract.quantity * 
                OptionProcessingConfig.SHARES_PER_CONTRACT
            )
            premium_pnl += (contract_premium - contract.fees)
        
        # ポジションをクリア
        self.long_contracts.clear()
        self.short_contracts.clear()
        
        return {
            'premium_pnl': premium_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

    def has_open_position(self) -> bool:
        """オープンポジションの有無を確認"""
        return bool(self.long_contracts or self.short_contracts)

    def get_remaining_quantity(self) -> Decimal:
        """残りの数量を取得"""
        long_qty = sum(c.quantity for c in self.long_contracts)
        short_qty = sum(c.quantity for c in self.short_contracts)
        return long_qty - short_qty

    def _calculate_pnl(self,
                     position_type: str,
                     open_price: Decimal,
                     close_price: Decimal,
                     open_fees: Decimal,
                     close_fees: Decimal,
                     quantity: Decimal) -> Decimal:
        """取引損益の計算"""
        contract_size = quantity * OptionProcessingConfig.SHARES_PER_CONTRACT
        
        if position_type == OptionProcessingConfig.POSITION_TYPES['LONG']:
            # 買い建ての場合: (売値 - 買値) * 契約サイズ - 手数料
            pnl = (close_price - open_price) * contract_size - (open_fees + close_fees)
        else:  
            # 売り建ての場合: (売値 - 買値) * 契約サイズ - 手数料
            pnl = (open_price - close_price) * contract_size - (open_fees + close_fees)
        
        return pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)