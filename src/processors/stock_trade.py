import re
from decimal import Decimal
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import date
from collections import defaultdict

from ..core.transaction import Transaction
from ..core.money import Money
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .trade_records import StockTradeRecord

@dataclass
class StockLot:
    """株式ロット（購入単位）を表すクラス"""
    quantity: Decimal
    price: Decimal
    acquisition_date: date
    fees: Decimal = Decimal('0')

class StockPosition:
    """株式ポジション管理クラス"""
    def __init__(self):
        self.lots: List[StockLot] = []
    
    def add_lot(self, lot: StockLot):
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
                remaining_quantity = Decimal('0')
            
            # 売却分の損益を計算
            cost_basis = lot.price * sold_quantity + lot.fees * (sold_quantity / lot.quantity)
            sale_proceed = price * sold_quantity - fees * (sold_quantity / quantity)
            realized_gain += sale_proceed - cost_basis
        
        return realized_gain

    def get_total_shares(self) -> Decimal:
        """保有株数の合計を取得"""
        return sum(lot.quantity for lot in self.lots)

class StockTradeProcessor(BaseProcessor[StockTradeRecord]):
    """株式取引の処理クラス（FIFO対応版）"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._positions: Dict[str, StockPosition] = defaultdict(StockPosition)
        self._assignments: Dict[str, List[Dict]] = defaultdict(list)
        self._matured_symbols: set = set()
    
    def process(self, transaction: Transaction) -> None:
        """株式取引トランザクションを処理"""
        # 満期トランザクションのシンボルを記憶し、過去のすべての取引を除外
        if self._is_matured_transaction(transaction):
            self._matured_symbols.add(transaction.symbol)
            # すでに記録された取引から同じシンボルの全ての取引を削除
            self.records = [
                record for record in self.records 
                if record.symbol != transaction.symbol
            ]
            return

        # 満期を迎えたシンボルに属する場合は除外
        if transaction.symbol in self._matured_symbols:
            return

        if not self._is_stock_trade(transaction):
            return
    
        self._process_stock_transaction(transaction)

    def record_option_assignment(self, symbol: str, date: date, quantity: int, strike_price: Decimal) -> None:
        """オプション権利行使情報を記録"""
        self._assignments[symbol].append({
            'date': date,
            'quantity': quantity,
            'strike_price': strike_price
        })

    def _process_stock_transaction(self, transaction: Transaction) -> None:
        """株式取引を処理"""
        symbol = transaction.symbol
        action = transaction.action_type.upper()
        quantity = Decimal(str(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))
        
        # オプション権利行使の影響を確認
        if action == 'BUY' and symbol in self._assignments:
            price = self._adjust_price_for_assignments(symbol, transaction.transaction_date, 
                                                     quantity, price)
        
        position = self._positions[symbol]
        realized_gain = Decimal('0')
        
        if action == 'BUY':
            # 買い取引
            lot = StockLot(
                quantity=quantity,
                price=price,
                acquisition_date=transaction.transaction_date,
                fees=fees
            )
            position.add_lot(lot)
        elif action == 'SELL':
            # 売り取引
            realized_gain = position.sell_shares(quantity, price, fees)
    
        trade_record = StockTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            action=transaction.action_type,
            quantity=quantity,
            price=Money(price),
            fees=Money(fees),
            realized_gain=Money(realized_gain),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date)
        )
    
        self.records.append(trade_record)

    def _adjust_price_for_assignments(self, symbol: str, date: date, 
                                    quantity: Decimal, price: Decimal) -> Decimal:
        """オプション権利行使による価格調整"""
        assignments = self._assignments[symbol]
        total_adjustment = Decimal('0')
        
        # 該当する権利行使を探す
        for assignment in assignments:
            if assignment['date'] == date:
                # 権利行使価格との差額を調整
                price_diff = assignment['strike_price'] - price
                total_adjustment += price_diff
        
        return price + total_adjustment if total_adjustment != 0 else price

    def _is_stock_trade(self, transaction: Transaction) -> bool:
        """株式取引トランザクションかどうかを判定"""
        if not transaction.symbol:
            return False
        
        stock_actions = {'BUY', 'SELL'}
        return (
            transaction.action_type.upper() in stock_actions and
            not self._is_option_symbol(transaction.symbol)
        )
    
    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))
    
    def _is_matured_transaction(self, transaction: Transaction) -> bool:
        """満期トランザクションかどうかを判定"""
        maturity_keywords = [
            'MATURITY', 
            'MATURED', 
            'CD MATURITY', 
            'BOND MATURITY', 
            'CD DEPOSIT FUNDS',
            'CD DEPOSIT ADJ',
            'FULL REDEMPTION'
        ]
        return transaction.action_type.upper() in [keyword.upper() for keyword in maturity_keywords]