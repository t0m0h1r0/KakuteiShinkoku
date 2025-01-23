from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re
import logging

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency
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
        
        # 同日取引の追跡用
        self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = defaultdict(lambda: defaultdict(list))
        # 取引の追跡情報
        self._transaction_tracking: Dict[str, Dict] = defaultdict(lambda: {
            'open_quantity': Decimal('0'),
            'close_quantity': Decimal('0'),
            'max_status': 'Open'
        })

    def process(self, transaction: Transaction) -> None:
        """単一のトランザクションを処理する基本メソッド"""
        # オプション取引でない場合はスキップ
        if not self._is_option_transaction(transaction):
            return

        # トランザクションを実際に処理
        self._process_transaction(transaction)

    def process_all(self, transactions: List[Transaction]) -> List[OptionTradeRecord]:
        """すべてのトランザクションを処理"""
        # 同日取引を追跡するための事前処理
        self._track_daily_transactions(transactions)
        
        # トランザクションの追跡情報をリセット
        self._transaction_tracking.clear()
        
        # 各シンボルの同日取引を処理
        for symbol, daily_symbol_txs in self._daily_transactions.items():
            # 日付順にソートして処理
            sorted_dates = sorted(daily_symbol_txs.keys())
            for transaction_date in sorted_dates:
                transactions_on_date = daily_symbol_txs[transaction_date]
                
                # 同日取引の処理
                self._process_daily_transactions(symbol, transactions_on_date)

        return self._trade_records

    def _track_daily_transactions(self, transactions: List[Transaction]) -> None:
        """同日取引を追跡"""
        for transaction in transactions:
            if self._is_option_transaction(transaction):
                symbol = transaction.symbol
                self._daily_transactions[symbol][transaction.transaction_date].append(transaction)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """同日の取引を処理"""
        # 取引をアクションでソート（Open → Closeの順、かつ数量の多い順）
        sorted_transactions = sorted(
            transactions, 
            key=lambda tx: (
                0 if self._normalize_action(tx.action_type).endswith('OPEN') else 1,
                -abs(Decimal(str(tx.quantity or 0)))
            )
        )
        
        # 取引追跡情報をリセット
        tracking = self._transaction_tracking[symbol]
        tracking['open_quantity'] = Decimal('0')
        tracking['close_quantity'] = Decimal('0')
        
        # トランザクションの処理
        for transaction in sorted_transactions:
            action = self._normalize_action(transaction.action_type)
            quantity = abs(Decimal(str(transaction.quantity or 0)))
            
            if action.endswith('OPEN'):
                tracking['open_quantity'] += quantity
            elif action.endswith('CLOSE'):
                tracking['close_quantity'] += quantity
            
            # トランザクションの処理
            self.process(transaction)
        
        # ステータスの更新：完全に決済されたかを正確に判定
        tracking['max_status'] = ('Closed' if tracking['close_quantity'] >= tracking['open_quantity'] 
                                  and tracking['open_quantity'] > 0 else 'Open')

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

        elif action in ['EXPIRED', 'ASSIGNED']:
            # 期限切れ処理
            pnl = position.handle_expiration(transaction.transaction_date)
            premium_pnl = pnl['premium_pnl']

        # 金額オブジェクトの作成
        price_money = self._create_money_with_rate(total_price, exchange_rate)
        fees_money = self._create_money_with_rate(fees, exchange_rate)
        trading_pnl_money = self._create_money_with_rate(trading_pnl, exchange_rate)
        premium_pnl_money = self._create_money_with_rate(premium_pnl, exchange_rate)

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
            position_type=self._determine_position_type(action),
            is_closed=not position.has_open_position(),
            is_expired=(action == 'EXPIRED'),
            is_assigned=(action == 'ASSIGNED')
        )
        
        self._trade_records.append(trade_record)
        self._update_summary_record(symbol, trade_record, option_info)

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

    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
        if not symbol:
            return False
        option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
        return bool(re.search(option_pattern, symbol))

    def _normalize_action(self, action: str) -> str:
        """アクションタイプを正規化"""
        action = action.upper().replace(' TO ', '_TO_')
        action = action.replace(' ', '')
        return action

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

    def get_records(self) -> List[OptionTradeRecord]:
        """取引記録の取得"""
        return sorted(self._trade_records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        """サマリー記録の取得"""
        # 既存のサマリーレコードが存在するものだけを返す
        summary_records = [
            record for record in self._summary_records.values()
            if record is not None  # nullチェック
        ]
        
        return sorted(
            summary_records,
            key=lambda x: (x.underlying or '', x.expiry_date or datetime.min.date(), x.strike_price or 0)
        )

    def _update_summary_record(self, symbol: str,
                             trade_record: OptionTradeRecord,
                             option_info: Dict) -> None:
        """サマリーレコードを更新"""
        position = self._positions[symbol]

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
                exchange_rate=trade_record.exchange_rate
            )
        
        summary = self._summary_records[symbol]
        
        # トランザクション追跡情報を取得
        tracking = self._transaction_tracking[symbol]
        
        # 残存数量の更新
        summary.remaining_quantity = position.get_remaining_quantity()

        # PNLと手数料の累積
        summary.trading_pnl += trade_record.trading_pnl
        summary.premium_pnl += trade_record.premium_pnl
        summary.total_fees += trade_record.fees

        # ステータスの判定
        if trade_record.is_expired:
            summary.status = 'Expired'
            summary.close_date = trade_record.trade_date

        elif trade_record.is_assigned:
            summary.status = 'Assigned'
            summary.close_date = trade_record.trade_date

        elif summary.remaining_quantity <= 0:
            summary.status = 'Closed'
            summary.close_date = trade_record.trade_date

        else:
            summary.status = 'Open'