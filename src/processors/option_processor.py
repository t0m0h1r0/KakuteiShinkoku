import re
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from ..core.transaction import Transaction
from ..core.money import Money, Currency
from ..core.interfaces import IExchangeRateProvider
from .base import BaseProcessor
from .option_records import OptionTradeRecord, OptionSummaryRecord
from .option_position import OptionContract, OptionPosition, ClosedTrade, ExpiredOption

class OptionProcessor(BaseProcessor):
    """オプション取引処理クラス"""
    
    def __init__(self, exchange_rate_provider: IExchangeRateProvider):
        super().__init__(exchange_rate_provider)
        self._positions: Dict[str, OptionPosition] = defaultdict(OptionPosition)
        self._trade_records: List[OptionTradeRecord] = []
        self._summary_records: Dict[str, OptionSummaryRecord] = {}

    def process(self, transaction: Transaction) -> None:
        """取引の処理"""
        if not self._is_option_transaction(transaction):
            return

        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        action = transaction.action_type.upper()
        symbol = transaction.symbol
        exchange_rate = self._get_exchange_rate(transaction.transaction_date)

        # 基本的な取引情報の作成
        quantity = abs(int(transaction.quantity or 0))
        price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))

        # 金額オブジェクトの作成
        price_money = self._create_money_with_rate(price, exchange_rate)
        fees_money = self._create_money_with_rate(fees, exchange_rate)

        # アクションに応じた処理
        if action in ['BUY_TO_OPEN', 'SELL_TO_OPEN']:
            trading_pnl, premium_pnl = self._handle_open_position(
                symbol, transaction.transaction_date, option_info,
                quantity, price, fees, action == 'BUY_TO_OPEN'
            )
        elif action in ['BUY_TO_CLOSE', 'SELL_TO_CLOSE']:
            trading_pnl, premium_pnl = self._handle_close_position(
                symbol, transaction.transaction_date, option_info,
                quantity, price, fees, action == 'BUY_TO_CLOSE'
            )
        elif action == 'EXPIRED':
            trading_pnl, premium_pnl = self._handle_expiration(
                symbol, transaction.transaction_date, option_info
            )
        else:
            return

        position = self._positions[symbol]
        is_closed = not position.get_position_summary()['has_position']

        # 取引記録の作成
        trading_pnl_money = self._create_money_with_rate(trading_pnl, exchange_rate)
        premium_pnl_money = self._create_money_with_rate(premium_pnl, exchange_rate)

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
            is_closed=is_closed,
            is_expired=(action == 'EXPIRED')
        )
        
        self._trade_records.append(trade_record)
        self._update_summary_record(symbol, trade_record, option_info)

    def _handle_open_position(self, symbol: str, trade_date: date,
                            option_info: Dict, quantity: int,
                            price: Decimal, fees: Decimal,
                            is_buy: bool) -> Tuple[Decimal, Decimal]:
        """オープンポジションの処理"""
        position = self._positions[symbol]
        contract = OptionContract(
            trade_date=trade_date,
            quantity=quantity,
            open_price=price,
            fees=fees,
            position_type='Long' if is_buy else 'Short'
        )
        position.add_contract(contract)
        return Decimal('0'), Decimal('0')  # 新規ポジションは損益なし

    def _handle_close_position(self, symbol: str, trade_date: date,
                             option_info: Dict, quantity: int,
                             price: Decimal, fees: Decimal,
                             is_buy: bool) -> Tuple[Decimal, Decimal]:
        """クローズポジションの処理"""
        position = self._positions[symbol]
        position.close_position(trade_date, quantity, price, fees, is_buy)
        pnl = position.calculate_total_pnl()
        return pnl['trading_pnl'], Decimal('0')  # 決済時は譲渡損益のみ

    def _handle_expiration(self, symbol: str, expire_date: date,
                         option_info: Dict) -> Tuple[Decimal, Decimal]:
        """満期時の処理"""
        position = self._positions[symbol]
        position.handle_expiration(expire_date)
        pnl = position.calculate_total_pnl()
        return Decimal('0'), pnl['premium_pnl']  # 満期時はプレミアム損益のみ

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
            
            summary.remaining_quantity = (
                self._positions[symbol].get_position_summary()['long_quantity'] -
                self._positions[symbol].get_position_summary()['short_quantity']
            )
            summary.trading_pnl += trade_record.trading_pnl
            summary.premium_pnl += trade_record.premium_pnl
            summary.total_fees += trade_record.fees

    def get_records(self) -> List[OptionTradeRecord]:
        """取引記録の取得"""
        return sorted(self._trade_records, key=lambda x: x.trade_date)

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        """サマリー記録の取得"""
        return sorted(
            self._summary_records.values(),
            key=lambda x: (x.underlying, x.expiry_date, x.strike_price)
        )

    def _is_option_transaction(self, transaction: Transaction) -> bool:
        """オプション取引かどうかを判定"""
        option_actions = {
            'BUY_TO_OPEN', 'SELL_TO_OPEN',
            'BUY_TO_CLOSE', 'SELL_TO_CLOSE',
            'EXPIRED', 'ASSIGNED'
        }
        return (
            transaction.action_type.upper() in option_actions and
            self._is_option_symbol(transaction.symbol)
        )

    def _is_option_symbol(self, symbol: str) -> bool:
        """オプションシンボルかどうかを判定"""
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
                    'option_type': option_type
                }
        except (ValueError, AttributeError):
            return None
        return None

    def _determine_position_type(self, action: str) -> str:
        """ポジションタイプを判定"""
        if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE']:
            return 'Long'
        return 'Short'