from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
import logging

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .option_records import OptionTradeRecord, OptionSummaryRecord
from .option_position import OptionPosition, OptionContract

class OptionProcessor(BaseProcessor):
    """オプション取引処理クラス"""
    
    # オプション1枚あたりの株数
    SHARES_PER_CONTRACT = 100
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._positions: Dict[str, OptionPosition] = defaultdict(OptionPosition)
        self._trade_records: List[OptionTradeRecord] = []
        self._summary_records: Dict[str, OptionSummaryRecord] = {}
        self._pending_transactions: Dict[str, List[Transaction]] = defaultdict(list)

    def process(self, transaction: Transaction) -> None:
        """取引の処理"""
        if not self._is_option_transaction(transaction):
            return

        symbol = transaction.symbol
        action = self._normalize_action(transaction.action_type)
        
        # 同一銘柄の未処理トランザクションがある場合は処理
        if symbol in self._pending_transactions:
            self._process_pending_transactions(symbol)

        # 新規取引がCLOSEで、同一銘柄のOPENが後に控えている可能性がある場合
        if action.endswith('CLOSE'):
            next_transactions = self._find_same_day_opens(transaction)
            if next_transactions:
                # CLOSEを保留にして、先にOPENを処理
                self._pending_transactions[symbol].append(transaction)
                for tx in next_transactions:
                    self._process_transaction(tx)
                return

        # 通常の処理
        self._process_transaction(transaction)

    def _process_transaction(self, transaction: Transaction) -> None:
        """トランザクションの実際の処理"""
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return
            
        # 基本情報の準備
        symbol = transaction.symbol
        action = self._normalize_action(transaction.action_type)
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)
        
        # 取引情報の作成
        quantity = abs(Decimal(str(transaction.quantity or 0)))
        per_share_price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))

        # ポジションの取得
        position = self._positions[symbol]

        # オプション価格とPNLの初期化
        total_price = Decimal('0')
        trading_pnl = Decimal('0')
        premium_pnl = Decimal('0')
        actual_delivery = Decimal('0')

        # アクションに応じた処理
        if action in ['BUY_TO_OPEN', 'SELL_TO_OPEN']:
            # 新規ポジションの作成
            contract = OptionContract(
                trade_date=transaction.transaction_date,
                quantity=quantity,
                price=per_share_price,
                fees=fees,
                position_type='Long' if action == 'BUY_TO_OPEN' else 'Short',
                option_type=option_info['option_type']
            )
            position.add_contract(contract)
            
            # プレミアムの計算
            if action == 'BUY_TO_OPEN':
                total_price = -per_share_price * self.SHARES_PER_CONTRACT * quantity
            else:
                total_price = per_share_price * self.SHARES_PER_CONTRACT * quantity

        elif action in ['BUY_TO_CLOSE', 'SELL_TO_CLOSE']:
            # 決済処理
            pnl = position.close_position(
                transaction.transaction_date,
                quantity,
                per_share_price,
                fees,
                action == 'BUY_TO_CLOSE'
            )
            trading_pnl = pnl['realized_gain']
            
            # 決済価格の設定
            if action == 'BUY_TO_CLOSE':
                total_price = -per_share_price * self.SHARES_PER_CONTRACT * quantity
            else:
                total_price = per_share_price * self.SHARES_PER_CONTRACT * quantity

        elif action == 'EXPIRED':
            # 期限切れ処理
            pnl = position.handle_expiration(transaction.transaction_date)
            premium_pnl = pnl['premium_pnl']

        elif action == 'ASSIGNED':
            # 権利行使処理
            pnl = position.handle_assignment(
                transaction.transaction_date,
                quantity,
                option_info['strike_price'],
                per_share_price,
                fees,
                option_info['option_type']
            )
            actual_delivery = pnl['actual_delivery']
            
            # 権利行使価格の設定
            if option_info['option_type'] == 'Call':
                total_price = -option_info['strike_price'] * self.SHARES_PER_CONTRACT * quantity
            else:  # Put
                total_price = option_info['strike_price'] * self.SHARES_PER_CONTRACT * quantity

        # 金額オブジェクトの作成
        price_money = self._create_money_with_rate(total_price, exchange_rate)
        fees_money = self._create_money_with_rate(fees, exchange_rate)
        trading_pnl_money = self._create_money_with_rate(trading_pnl, exchange_rate)
        premium_pnl_money = self._create_money_with_rate(premium_pnl, exchange_rate)
        actual_delivery_money = self._create_money_with_rate(actual_delivery, exchange_rate)

        # 取引記録の作成
        trade_record = OptionTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=price_money,
            fees=fees_money,
            exchange_rate=exchange_rate,
            option_type=option_info['option_type'],
            strike_price=option_info['strike_price'],
            expiry_date=option_info['expiry_date'],
            underlying=option_info['underlying'],
            trading_pnl=trading_pnl_money,
            premium_pnl=premium_pnl_money,
            actual_delivery=actual_delivery_money,
            position_type=self._determine_position_type(action),
            is_closed=not position.has_open_position(),
            is_expired=(action == 'EXPIRED'),
            is_assigned=(action == 'ASSIGNED')
        )
        
        self._trade_records.append(trade_record)
        self._update_summary_record(symbol, trade_record, option_info)

    def _find_same_day_opens(self, transaction: Transaction) -> List[Transaction]:
        """同日のOPEN取引を検索"""
        opens = []
        target_date = transaction.transaction_date
        target_symbol = transaction.symbol
        
        for future_tx in self._future_transactions(transaction):
            if (future_tx.transaction_date == target_date and 
                future_tx.symbol == target_symbol and
                self._normalize_action(future_tx.action_type).endswith('OPEN')):
                opens.append(future_tx)
        
        return opens

    def _future_transactions(self, current_transaction: Transaction) -> List[Transaction]:
        """現在の取引以降のトランザクションを取得"""
        found_current = False
        future_txs = []
        
        for tx in self.transactions:
            if tx == current_transaction:
                found_current = True
                continue
            
            if found_current:
                future_txs.append(tx)
                
        return future_txs

    def _process_pending_transactions(self, symbol: str) -> None:
        """保留中のトランザクションを処理"""
        if symbol in self._pending_transactions:
            pending = self._pending_transactions[symbol]
            self._pending_transactions[symbol] = []
            
            for tx in pending:
                self._process_transaction(tx)

    def get_records(self) -> List[OptionTradeRecord]:
        """取引記録の取得"""
        return sorted(self._trade_records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        """サマリー記録の取得"""
        return sorted(
            self._summary_records.values(),
            key=lambda x: (x.underlying, x.expiry_date, x.strike_price)
        )

    def process_all(self, transactions: List[Transaction]) -> List[OptionTradeRecord]:
        """すべてのトランザクションを処理"""
        self.transactions = transactions  # 後で同日取引を検索するために保持
        result = super().process_all(transactions)
        self.transactions = None  # クリーンアップ
        return result

    def _is_option_transaction(self, transaction: Transaction) -> bool:
        """オプション取引かどうかを判定"""
        normalized_action = self._normalize_action(transaction.action_type)
        option_actions = {
            'BUY_TO_OPEN', 'SELL_TO_OPEN',
            'BUY_TO_CLOSE', 'SELL_TO_CLOSE',
            'EXPIRED', 'ASSIGNED'
        }
        return (
            normalized_action in option_actions and
            self._is_option_symbol(transaction.symbol)
        )

    def _normalize_action(self, action: str) -> str:
        """アクションタイプを正規化"""
        action = action.upper().replace(' TO ', '_TO_')
        action = action.replace(' ', '')
        return action

    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        if not symbol:
            return False
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))

    def _parse_option_info(self, symbol: str) -> Optional[Dict]:
        """オプションシンボルを解析"""
        try:
            pattern = r'(\w+)\s+(\d{2}/\d{2}/\d{4})\s+(\d+\.\d+)\s+([CP])'
            match = re.match(pattern, symbol)
            if match:
                underlying, expiry, strike, option_type = match.groups()
                return {
                    'underlying': underlying,
                    'expiry_date': datetime.strptime(expiry, '%m/%d/%Y').date(),
                    'strike_price': Decimal(strike),
                    'option_type': 'Call' if option_type == 'C' else 'Put'
                }
        except (ValueError, AttributeError) as e:
            self.logger.warning(f"Error parsing option symbol {symbol}: {e}")
            return None
        return None

    def _determine_position_type(self, action: str) -> str:
        """ポジションタイプを判定"""
        if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE']:
            return 'Long'
        return 'Short'

    def _update_summary_record(self, symbol: str,
                             trade_record: OptionTradeRecord,
                             option_info: Dict) -> None:
        """サマリー記録の更新"""
        if symbol not in self._summary_records:
            self._summary_records[symbol] = OptionSummaryRecord(
                account_id=trade_record.account_id,
                symbol=symbol,
                description=trade_record.description,
                underlying=option_info['underlying'],
                option_type=option_info['option_type'],
                strike_price=option_info['strike_price'],
                expiry_date=option_info['expiry_date'],
                open_date=trade_record.trade_date,
                close_date=None,
                status='Open',
                initial_quantity=trade_record.quantity,
                remaining_quantity=trade_record.quantity,
                trading_pnl=trade_record.trading_pnl,
                premium_pnl=trade_record.premium_pnl,
                actual_delivery=trade_record.actual_delivery,
                total_fees=trade_record.fees,
                exchange_rate=trade_record.exchange_rate
            )
        else:
            summary = self._summary_records[symbol]
            if trade_record.is_closed:
                summary.status = 'Closed'
                summary.close_date = trade_record.trade_date
            elif trade_record.is_expired:
                summary.status = 'Expired'
                summary.close_date = trade_record.trade_date
            elif trade_record.is_assigned:
                summary.status = 'Assigned'
                summary.close_date = trade_record.trade_date
            
            position = self._positions[symbol]
            summary.remaining_quantity = position.get_remaining_quantity()
            summary.trading_pnl += trade_record.trading_pnl
            summary.premium_pnl += trade_record.premium_pnl
            summary.actual_delivery += trade_record.actual_delivery
            summary.total_fees += trade_record.fees