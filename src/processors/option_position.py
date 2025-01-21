from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional

@dataclass
class OptionContract:
    """オプション契約情報"""
    trade_date: date
    quantity: Decimal  # intからDecimalに変更
    open_price: Decimal
    fees: Decimal
    position_type: str  # 'Long' or 'Short'

    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.open_price, (int, float)):
            self.open_price = Decimal(str(self.open_price))
        if isinstance(self.fees, (int, float)):
            self.fees = Decimal(str(self.fees))

@dataclass
class ClosedTrade:
    """決済済み取引情報"""
    open_date: date
    close_date: date
    quantity: Decimal  # intからDecimalに変更
    open_price: Decimal
    close_price: Decimal
    open_fees: Decimal
    close_fees: Decimal
    position_type: str
    pnl: Decimal

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
        if isinstance(self.pnl, (int, float)):
            self.pnl = Decimal(str(self.pnl))

@dataclass
class ExpiredOption:
    """期限満了オプション情報"""
    open_date: date
    expire_date: date
    quantity: Decimal  # intからDecimalに変更
    premium: Decimal
    fees: Decimal
    position_type: str

    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.premium, (int, float)):
            self.premium = Decimal(str(self.premium))
        if isinstance(self.fees, (int, float)):
            self.fees = Decimal(str(self.fees))

class OptionPosition:
    """オプションポジション管理クラス"""
    def __init__(self):
        self.long_contracts: List[OptionContract] = []
        self.short_contracts: List[OptionContract] = []
        self.closed_trades: List[ClosedTrade] = []
        self.expired_options: List[ExpiredOption] = []
        
    def add_contract(self, contract: OptionContract) -> None:
        """契約を追加"""
        if contract.position_type == 'Long':
            self.long_contracts.append(contract)
        else:
            self.short_contracts.append(contract)

    def close_position(self, trade_date: date, quantity: Decimal,
                      price: Decimal, fees: Decimal, is_buy: bool) -> None:
        """ポジションをクローズ"""
        # 整数型をDecimal型に変換
        if isinstance(quantity, int):
            quantity = Decimal(str(quantity))
        if isinstance(price, (int, float)):
            price = Decimal(str(price))
        if isinstance(fees, (int, float)):
            fees = Decimal(str(fees))

        contracts = self.short_contracts if is_buy else self.long_contracts
        remaining_quantity = quantity
        
        while remaining_quantity > 0 and contracts:
            contract = contracts[0]
            close_quantity = min(remaining_quantity, contract.quantity)
            
            # プレミアムの計算（符号の調整）
            close_price_per_unit = price * close_quantity / quantity
            close_fees_per_unit = fees * close_quantity / quantity
            
            # 決済した数量分を記録
            self.closed_trades.append(ClosedTrade(
                open_date=contract.trade_date,
                close_date=trade_date,
                quantity=close_quantity,
                open_price=contract.open_price * close_quantity / contract.quantity,
                close_price=close_price_per_unit,
                open_fees=contract.fees * close_quantity / contract.quantity,
                close_fees=close_fees_per_unit,
                position_type=contract.position_type,
                pnl=self._calculate_pnl(
                    contract.position_type,
                    contract.open_price * close_quantity / contract.quantity,
                    close_price_per_unit,
                    contract.fees * close_quantity / contract.quantity,
                    close_fees_per_unit
                )
            ))
            
            # 残数量を更新
            if close_quantity == contract.quantity:
                contracts.pop(0)
            else:
                contract.quantity -= close_quantity
                contract.open_price = contract.open_price * (contract.quantity - close_quantity) / contract.quantity
                contract.fees = contract.fees * (contract.quantity - close_quantity) / contract.quantity
            
            remaining_quantity -= close_quantity

    def handle_expiration(self, expire_date: date) -> None:
        """期限満了処理"""
        # ロングポジションの処理
        for contract in self.long_contracts:
            self.expired_options.append(ExpiredOption(
                open_date=contract.trade_date,
                expire_date=expire_date,
                quantity=contract.quantity,
                premium=-contract.open_price,  # ロングはプレミアム支払い
                fees=contract.fees,
                position_type='Long'
            ))
        self.long_contracts.clear()

        # ショートポジションの処理
        for contract in self.short_contracts:
            self.expired_options.append(ExpiredOption(
                open_date=contract.trade_date,
                expire_date=expire_date,
                quantity=contract.quantity,
                premium=contract.open_price,  # ショートはプレミアム受取
                fees=contract.fees,
                position_type='Short'
            ))
        self.short_contracts.clear()

    def get_position_summary(self) -> Dict:
        """ポジション情報の取得"""
        long_quantity = sum(c.quantity for c in self.long_contracts)
        short_quantity = sum(c.quantity for c in self.short_contracts)
        
        return {
            'long_quantity': long_quantity,
            'short_quantity': short_quantity,
            'has_position': long_quantity > 0 or short_quantity > 0
        }

    def calculate_total_pnl(self) -> Dict[str, Decimal]:
        """損益計算"""
        # 譲渡損益（反対売買による損益）
        trading_pnl = Decimal('0')
        for trade in self.closed_trades:
            if isinstance(trade.pnl, (int, float)):
                trading_pnl += Decimal(str(trade.pnl))
            else:
                trading_pnl += trade.pnl
        
        # プレミアム損益（期限満了分の損益）
        premium_pnl = Decimal('0')
        for opt in self.expired_options:
            if isinstance(opt.premium, (int, float)):
                premium = Decimal(str(opt.premium))
            else:
                premium = opt.premium
                
            if isinstance(opt.fees, (int, float)):
                fees = Decimal(str(opt.fees))
            else:
                fees = opt.fees
                
            premium_pnl += premium - fees
        
        return {
            'trading_pnl': trading_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'premium_pnl': premium_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_pnl': (trading_pnl + premium_pnl).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

    @staticmethod
    def _calculate_pnl(position_type: str, open_price: Decimal,
                      close_price: Decimal, open_fees: Decimal,
                      close_fees: Decimal) -> Decimal:
        """個別取引の損益計算"""
        if position_type == 'Long':
            return (close_price - open_price - (open_fees + close_fees)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:  # Short
            return (open_price - close_price - (open_fees + close_fees)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )