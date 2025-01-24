from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
import logging

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency
from ..exchange.rate_provider import RateProvider
from .base import BaseProcessor
from .option_records import OptionTradeRecord, OptionSummaryRecord
from .option_position import OptionPosition, OptionContract

class OptionProcessingConfig:
    """オプション処理の設定と定数"""
    SHARES_PER_CONTRACT = 100
    OPTION_ACTIONS = {
        'BUY_TO_OPEN', 'SELL_TO_OPEN',
        'BUY_TO_CLOSE', 'SELL_TO_CLOSE',
        'EXPIRED', 'ASSIGNED'
    }
    OPTION_SYMBOL_PATTERN = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'

class OptionTransactionTracker:
    """オプション取引の状態を追跡するクラス"""
    def __init__(self):
        self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = defaultdict(lambda: defaultdict(list))
        self._transaction_tracking: Dict[str, Dict] = defaultdict(lambda: {
            'open_quantity': Decimal('0'),
            'close_quantity': Decimal('0'),
            'max_status': 'Open'
        })

    def track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """日次トランザクションを追跡"""
        for transaction in transactions:
            symbol = transaction.symbol
            self._daily_transactions[symbol][transaction.transaction_date].append(transaction)

    def get_processed_transactions(self, symbol: str) -> List[Dict]:
        """特定のシンボルの処理済みトランザクションを取得"""
        return self._transaction_tracking.get(symbol, {})

    def update_tracking(self, symbol: str, action: str, quantity: Decimal) -> None:
        """取引状態を更新"""
        tracking = self._transaction_tracking[symbol]
        
        if action.endswith('OPEN'):
            tracking['open_quantity'] += quantity
        elif action.endswith('CLOSE'):
            tracking['close_quantity'] += quantity
        
        tracking['max_status'] = 'Closed' if (
            tracking['close_quantity'] >= tracking['open_quantity'] 
            and tracking['open_quantity'] > 0
        ) else 'Open'

class OptionProcessor(BaseProcessor):
    """オプション取引処理のメインプロセッサ"""
    def __init__(self):
        super().__init__()
        self._positions: Dict[str, OptionPosition] = defaultdict(OptionPosition)
        self._trade_records: List[OptionTradeRecord] = []
        self._summary_records: Dict[str, OptionSummaryRecord] = {}
        self._transaction_tracker = OptionTransactionTracker()

    def process_all(self, transactions: List[Transaction]) -> List[OptionTradeRecord]:
        """全トランザクションを処理"""
        try:
            # 日次トランザクションの追跡
            self._transaction_tracker.track_daily_transactions(transactions)
            
            # シンボルごとに処理
            for symbol, daily_symbol_txs in self._transaction_tracker._daily_transactions.items():
                sorted_dates = sorted(daily_symbol_txs.keys())
                for transaction_date in sorted_dates:
                    transactions_on_date = daily_symbol_txs[transaction_date]
                    self._process_daily_transactions(symbol, transactions_on_date)

            return self._trade_records

        except Exception as e:
            self.logger.error(f"オプション取引処理中にエラーが発生: {e}")
            return []

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        # トランザクションをアクションタイプと数量でソート
        sorted_transactions = self._sort_transactions(transactions)
        
        # トランザクション処理
        for transaction in sorted_transactions:
            if self._is_option_transaction(transaction):
                self._process_transaction(transaction)

    def _sort_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """トランザクションのソート"""
        return sorted(
            transactions, 
            key=lambda tx: (
                0 if self._normalize_action(tx.action_type).endswith('OPEN') else 1,
                -abs(Decimal(str(tx.quantity or 0)))
            )
        )

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションの処理"""
        try:
            if self._is_option_transaction(transaction):
                self._process_transaction(transaction)
        except Exception as e:
            self.logger.error(f"オプション取引の処理中にエラー: {transaction} - {e}")

    def _process_transaction(self, transaction: Transaction) -> None:
        """オプション取引の詳細処理"""
        # オプション情報の解析
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return
        
        symbol = transaction.symbol
        action = self._normalize_action(transaction.action_type)
        
        # 数量と価格の取得
        quantity, per_share_price, fees = self._get_transaction_details(transaction)

        position = self._positions[symbol]
        
        # 取引タイプに応じた処理
        trading_result = self._handle_transaction_type(
            position, action, quantity, per_share_price, fees, transaction.transaction_date
        )

        # トレードレコードの作成
        trade_record = self._create_trade_record(
            transaction, symbol, option_info, action, 
            quantity, per_share_price, fees, trading_result
        )
        
        self._trade_records.append(trade_record)
        self._update_summary_record(symbol, trade_record, option_info)
        
        # トランザクショントラッカーの更新
        self._transaction_tracker.update_tracking(symbol, action, quantity)

    def _get_transaction_details(self, transaction: Transaction) -> Tuple[Decimal, Decimal, Decimal]:
        """取引の数量、価格、手数料を取得"""
        quantity = abs(Decimal(str(transaction.quantity or 0)))
        per_share_price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))
        return quantity, per_share_price, fees

    def _handle_transaction_type(
        self, 
        position: OptionPosition, 
        action: str, 
        quantity: Decimal, 
        per_share_price: Decimal, 
        fees: Decimal, 
        trade_date: date
    ) -> Dict:
        """取引タイプに応じた処理"""
        total_price = Decimal('0')
        trading_pnl = Decimal('0')
        premium_pnl = Decimal('0')

        if action in ['BUY_TO_OPEN', 'SELL_TO_OPEN']:
            contract = OptionContract(
                trade_date=trade_date,
                quantity=quantity,
                price=per_share_price,
                fees=fees,
                position_type='Long' if action == 'BUY_TO_OPEN' else 'Short',
                option_type=self._determine_option_type(action)
            )
            position.add_contract(contract)
            
            total_price = (-per_share_price if action == 'BUY_TO_OPEN' else per_share_price) * OptionProcessingConfig.SHARES_PER_CONTRACT * quantity

        elif action in ['BUY_TO_CLOSE', 'SELL_TO_CLOSE']:
            pnl = position.close_position(
                trade_date,
                quantity,
                per_share_price,
                fees,
                action == 'BUY_TO_CLOSE'
            )
            trading_pnl = pnl['realized_gain']
            
            total_price = (-per_share_price if action == 'BUY_TO_CLOSE' else per_share_price) * OptionProcessingConfig.SHARES_PER_CONTRACT * quantity

        elif action in ['EXPIRED', 'ASSIGNED']:
            pnl = position.handle_expiration(trade_date)
            premium_pnl = pnl['premium_pnl']

        return {
            'total_price': total_price,
            'trading_pnl': trading_pnl,
            'premium_pnl': premium_pnl
        }

    def _create_trade_record(
        self, 
        transaction: Transaction,
        symbol: str, 
        option_info: Dict, 
        action: str, 
        quantity: Decimal, 
        per_share_price: Decimal, 
        fees: Decimal, 
        trading_result: Dict
    ) -> OptionTradeRecord:
        """トレードレコードの作成"""
        price_money = self._create_money(trading_result['total_price'])
        fees_money = self._create_money(fees)
        trading_pnl_money = self._create_money(trading_result['trading_pnl'])
        premium_pnl_money = self._create_money(trading_result['premium_pnl'])

        position = self._positions[symbol]

        return OptionTradeRecord(
            trade_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            price=price_money,
            fees=fees_money,
            exchange_rate=RateProvider().get_rate(Currency.USD,Currency.JPY,transaction.transaction_date).rate,
            option_type=option_info['option_type'],
            strike_price=option_info['strike_price'],
            expiry_date=option_info['expiry_date'],
            underlying=option_info['underlying'],
            trading_pnl=trading_pnl_money,
            premium_pnl=premium_pnl_money,
            position_type=self._determine_position_type(action),
            is_closed=not position.has_open_position(),
            is_expired=(action == 'EXPIRED'),
            is_assigned=(action == 'ASSIGNED')
        )

    @staticmethod
    def _is_option_transaction(transaction: Transaction) -> bool:
        """オプション取引かどうかを判定"""
        normalized_action = OptionProcessor._normalize_action(transaction.action_type)
        return (
            normalized_action in OptionProcessingConfig.OPTION_ACTIONS and 
            OptionProcessor._is_option_symbol(transaction.symbol)
        )

    @staticmethod
    def _is_option_symbol(symbol: str) -> bool:
        """オプションシンボルの検証"""
        if not symbol:
            return False
        return bool(re.search(OptionProcessingConfig.OPTION_SYMBOL_PATTERN, symbol))

    @staticmethod
    def _normalize_action(action: str) -> str:
        """アクション名の正規化"""
        return action.upper().replace(' TO ', '_TO_').replace(' ', '')

    def _parse_option_info(self, symbol: str) -> Optional[Dict]:
        """オプション情報のパース"""
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
            self.logger.warning(f"オプションシンボルのパースに失敗: {symbol} - {e}")
        return None

    def _determine_option_type(self, action: str) -> str:
        """オプションタイプの決定"""
        return 'Call' if 'BUY' in action.upper() else 'Put'

    @staticmethod
    def _determine_position_type(action: str) -> str:
        """ポジションタイプの決定"""
        return 'Long' if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE'] else 'Short'

    def get_records(self) -> List[OptionTradeRecord]:
        """トレードレコードの取得"""
        return sorted(self._trade_records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        """サマリーレコードの取得"""
        summary_records = [
            record for record in self._summary_records.values()
            if record is not None
        ]
        
        return sorted(
            summary_records,
            key=lambda x: (x.underlying or '', x.expiry_date or datetime.min.date(), x.strike_price or 0)
        )

    def _update_summary_record(
        self, 
        symbol: str, 
        trade_record: OptionTradeRecord, 
        option_info: Dict
    ) -> None:
        """サマリーレコードの更新"""
        position = self._positions[symbol]

        # 初回のサマリーレコード作成
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
                total_fees=trade_record.fees,
            )
        
        # サマリーレコードの更新
        summary = self._summary_records[symbol]
        summary.remaining_quantity = position.get_remaining_quantity()
        summary.trading_pnl += trade_record.trading_pnl
        summary.premium_pnl += trade_record.premium_pnl
        summary.total_fees += trade_record.fees

        # ステータスの更新
        if trade_record.is_expired:
            summary.status = 'Expired'
            summary.close_date = trade_record.trade_date
        elif trade_record.is_assigned:
            summary.status = 'Assigned'
            summary.close_date = trade_record.trade_date
        elif summary.remaining_quantity <= 0:
            summary.status = 'Closed'
            summary.close_date = trade_record.trade_date