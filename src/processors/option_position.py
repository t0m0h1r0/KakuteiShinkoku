from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
from typing import List, Dict, Optional, Any

SHARES_PER_CONTRACT = 100  # オプション1枚あたりの株数

@dataclass
class OptionContract:
    """オプション契約情報"""
    trade_date: date
    quantity: Decimal
    open_price: Decimal
    fees: Decimal
    position_type: str  # 'Long' or 'Short'
    option_type: str   # 'Call' or 'Put'

    def __post_init__(self):
        """データ型の変換"""
        if isinstance(self.quantity, int):
            self.quantity = Decimal(str(self.quantity))
        if isinstance(self.open_price, (int, float)):
            self.open_price = Decimal(str(self.open_price))
        if isinstance(self.fees, (int, float)):
            self.fees = Decimal(str(self.fees))

@dataclass
class AssignedOption:
    """権利行使オプション情報"""
    contract: OptionContract
    assignment_date: date
    assignment_price: Decimal
    underlying_transaction_details: Dict[str, Any]

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
    position_type: str
    realized_gain: Decimal
    is_assigned: bool = False
    assignment_details: Optional[Dict[str, Any]] = None

@dataclass
class ExpiredOption:
    """期限満了オプション情報"""
    open_date: date
    expire_date: date
    quantity: Decimal
    premium: Decimal
    fees: Decimal
    position_type: str

class OptionPosition:
    """オプションポジション管理クラス"""
    def __init__(self):
        self.long_contracts: List[OptionContract] = []
        self.short_contracts: List[OptionContract] = []
        self.closed_trades: List[ClosedTrade] = []
        self.expired_options: List[ExpiredOption] = []
        self.assigned_options: List[AssignedOption] = []
        
    def add_contract(self, contract: OptionContract) -> None:
        """契約を追加"""
        if contract.position_type == 'Long':
            self.long_contracts.append(contract)
        else:
            self.short_contracts.append(contract)

    def close_position(self, trade_date: date, quantity: Decimal,
                      price: Decimal, fees: Decimal, is_buy: bool,
                      is_assigned: bool = False,
                      assignment_details: Optional[Dict[str, Any]] = None) -> None:
        """ポジションをクローズ"""
        # 整数型をDecimal型に変換
        quantity = Decimal(str(quantity)) if isinstance(quantity, int) else quantity
        price = Decimal(str(price)) if isinstance(price, (int, float)) else price
        fees = Decimal(str(fees)) if isinstance(fees, (int, float)) else fees

        # is_buyがTrueの場合は空売りの決済（short_contractsを使用）
        # is_buyがFalseの場合は買い建ての決済（long_contractsを使用）
        contracts = self.short_contracts if is_buy else self.long_contracts
        remaining_quantity = quantity
        
        while remaining_quantity > 0 and contracts:
            contract = contracts[0]
            close_quantity = min(remaining_quantity, contract.quantity)
            
            # 決済価格と手数料を計算
            close_price = price
            close_fees = fees * (close_quantity / quantity)
            
            # 決済した数量分を記録
            self.closed_trades.append(ClosedTrade(
                open_date=contract.trade_date,
                close_date=trade_date,
                quantity=close_quantity,
                open_price=contract.open_price,
                close_price=close_price,
                open_fees=contract.fees * (close_quantity / contract.quantity),
                close_fees=close_fees,
                position_type=contract.position_type,
                realized_gain=self._calculate_realized_gain(
                    contract.position_type,
                    contract.open_price,
                    close_price,
                    contract.fees * (close_quantity / contract.quantity),
                    close_fees,
                    close_quantity
                ),
                is_assigned=is_assigned,
                assignment_details=assignment_details
            ))
            
            # 残数量を更新
            if close_quantity == contract.quantity:
                contracts.pop(0)
            else:
                contract.quantity -= close_quantity
                contract.fees = contract.fees * (contract.quantity / (contract.quantity + close_quantity))
            
            remaining_quantity -= close_quantity

    def handle_assignment(self, contract: OptionContract, 
                          assignment_date: date, 
                          assignment_price: Decimal,
                          underlying_transaction_details: Dict[str, Any]) -> None:
        """オプション権利行使の処理"""
        # ショートポジションの場合のみ権利行使を処理
        if contract.position_type != 'Short':
            return

        # 権利行使オブジェクトを作成
        assigned_option = AssignedOption(
            contract=contract,
            assignment_date=assignment_date,
            assignment_price=assignment_price,
            underlying_transaction_details=underlying_transaction_details
        )
        
        # 権利行使オプションリストに追加
        self.assigned_options.append(assigned_option)
        
        # ポジションをクローズ（権利行使として）
        self.close_position(
            trade_date=assignment_date, 
            quantity=contract.quantity, 
            price=assignment_price, 
            fees=Decimal('0'),  # 権利行使時の手数料を0として扱う
            is_buy=True,  # ショートポジションの権利行使は買い取りとして扱う
            is_assigned=True,
            assignment_details={
                'assignment_price': assignment_price,
                'underlying_transaction': underlying_transaction_details
            }
        )

    def handle_expiration(self, expire_date: date) -> None:
        """期限満了処理"""
        # ロングポジションの処理
        for contract in self.long_contracts:
            self.expired_options.append(ExpiredOption(
                open_date=contract.trade_date,
                expire_date=expire_date,
                quantity=contract.quantity,
                premium=-contract.open_price * contract.quantity,  # ロングはプレミアム支払い
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
                premium=contract.open_price * contract.quantity,  # ショートはプレミアム受取
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
        trading_pnl = sum((trade.realized_gain for trade in self.closed_trades), Decimal('0'))
        
        # プレミアム損益（期限満了分の損益）
        premium_pnl = Decimal('0')
        for opt in self.expired_options:
            premium_pnl += opt.premium - opt.fees
        
        return {
            'trading_pnl': trading_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'premium_pnl': premium_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'total_pnl': (trading_pnl + premium_pnl).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }

    def get_assigned_details(self) -> List[Dict[str, Any]]:
        """権利行使の詳細を取得"""
        return [
            {
                'contract': {
                    'trade_date': opt.contract.trade_date,
                    'quantity': opt.contract.quantity,
                    'open_price': opt.contract.open_price,
                    'option_type': opt.contract.option_type
                },
                'assignment_date': opt.assignment_date,
                'assignment_price': opt.assignment_price,
                'underlying_transaction': opt.underlying_transaction_details
            }
            for opt in self.assigned_options
        ]

    @staticmethod
    def _calculate_realized_gain(position_type: str, open_price: Decimal,
                               close_price: Decimal, open_fees: Decimal,
                               close_fees: Decimal, quantity: Decimal) -> Decimal:
        """個別取引の損益計算"""
        # 1枚あたりの損益を計算（100株 = 1枚として計算）
        if position_type == 'Long':
            # 買い建ての場合: (売値 - 買値) * 数量 * 100株 - 手数料
            gain = ((close_price - open_price) * quantity * SHARES_PER_CONTRACT) - (open_fees + close_fees)
        else:  # Short
            # 売り建ての場合: (売値 - 買値) * 数量 * 100株 - 手数料
            gain = ((open_price - close_price) * quantity * SHARES_PER_CONTRACT) - (open_fees + close_fees)
        
        return gain.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)