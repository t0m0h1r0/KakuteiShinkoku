from typing import Dict, List, Optional, Any
from datetime import date, datetime
from decimal import Decimal
import re
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency
from ...exchange.exchange import exchange

from .record import OptionTradeRecord, OptionSummaryRecord
from .position import OptionPosition, OptionContract
from .tracker import OptionTransactionTracker
from .config import OptionProcessingConfig

class OptionProcessor(BaseProcessor[OptionTradeRecord, OptionSummaryRecord]):
    def __init__(self) -> None:
        super().__init__()
        self._positions: Dict[str, OptionPosition] = {}
        self._transaction_tracker = OptionTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        option_transactions = [t for t in transactions if self._is_option_transaction(t)]
        
        if option_transactions:
            sorted_transactions = sorted(
                option_transactions, 
                key=lambda tx: (
                    0 if self._normalize_action(tx.action_type).endswith('OPEN') else 1,
                    -abs(Decimal(str(tx.quantity or 0)))
                )
            )
            
            for transaction in sorted_transactions:
                self.process(transaction)

    def process(self, transaction: Transaction) -> None:
        try:
            if not self._is_option_transaction(transaction):
                return

            option_info = self._parse_option_info(transaction.symbol)
            if not option_info:
                return

            self._process_option_transaction(transaction, option_info)

        except Exception as e:
            self.logger.error(f"オプション取引の処理中にエラー: {transaction} - {e}")

    def _process_option_transaction(self, transaction: Transaction, option_info: Dict[str, Any]) -> None:
        try:
            symbol = transaction.symbol
            action = self._normalize_action(transaction.action_type)
            quantity = abs(Decimal(str(transaction.quantity or 0)))
            per_share_price = Decimal(str(transaction.price or 0))
            fees = Decimal(str(transaction.fees or 0))

            position = self._get_or_create_position(symbol)
            trading_result = self._handle_transaction_type(
                position, action, quantity, per_share_price, fees, transaction.transaction_date
            )

            price_money = Money(per_share_price * quantity, Currency.USD, transaction.transaction_date)
            fees_money = Money(fees, Currency.USD, transaction.transaction_date)
            trading_pnl_money = Money(trading_result.get('trading_pnl', 0), Currency.USD, transaction.transaction_date)
            premium_pnl_money = Money(trading_result.get('premium_pnl', 0), Currency.USD, transaction.transaction_date)

            record = OptionTradeRecord(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=symbol,
                description=transaction.description,
                action=action,
                quantity=quantity,
                option_type=option_info['option_type'],
                strike_price=option_info['strike_price'],
                expiry_date=option_info['expiry_date'],
                underlying=option_info['underlying'],
                price=price_money,
                fees=fees_money,
                trading_pnl=trading_pnl_money,
                premium_pnl=premium_pnl_money,
                exchange_rate=price_money.get_rate(),
                position_type=self._determine_position_type(action),
                is_closed=not position.has_open_position(),
                is_expired=(action == 'EXPIRED'),
                is_assigned=(action == 'ASSIGNED')
            )
            
            self._trade_records.append(record)
            self._update_summary_record(symbol, record, option_info)
            
            self._transaction_tracker.update_tracking(
                symbol, action, quantity, 
                {'trading_pnl': trading_result.get('trading_pnl', 0),
                 'premium_pnl': trading_result.get('premium_pnl', 0)}
            )

        except Exception as e:
            self.logger.error(f"オプション取引処理中にエラー: {e}")
            raise

    def _get_or_create_position(self, symbol: str) -> OptionPosition:
        if symbol not in self._positions:
            self._positions[symbol] = OptionPosition()
        return self._positions[symbol]

    def _handle_transaction_type(
        self, 
        position: OptionPosition, 
        action: str, 
        quantity: Decimal, 
        per_share_price: Decimal, 
        fees: Decimal, 
        trade_date: date
    ) -> Dict[str, Decimal]:
        total_price = Decimal('0')
        trading_pnl = Decimal('0')
        premium_pnl = Decimal('0')

        if action in OptionProcessingConfig.ACTION_TYPES['OPEN']:
            contract = OptionContract(
                trade_date=trade_date,
                quantity=quantity,
                price=per_share_price,
                fees=fees,
                position_type=OptionProcessingConfig.POSITION_TYPES['LONG' if action == 'BUY_TO_OPEN' else 'SHORT'],
                option_type=self._determine_option_type(action)
            )
            position.add_contract(contract)
            total_price = (-per_share_price if action == 'BUY_TO_OPEN' else per_share_price) * quantity * 100

        elif action in OptionProcessingConfig.ACTION_TYPES['CLOSE']:
            pnl = position.close_position(trade_date, quantity, per_share_price, fees, action == 'BUY_TO_CLOSE')
            trading_pnl = pnl['realized_gain']
            total_price = (-per_share_price if action == 'BUY_TO_CLOSE' else per_share_price) * quantity * 100

        elif action in ['EXPIRED', 'ASSIGNED']:
            pnl = position.handle_expiration(trade_date)
            premium_pnl = pnl['premium_pnl']

        return {
            'total_price': total_price,
            'trading_pnl': trading_pnl,
            'premium_pnl': premium_pnl
        }

    @staticmethod
    def _normalize_action(action: str) -> str:
        return action.upper().replace(' TO ', '_TO_').replace(' ', '')

    @staticmethod
    def _is_option_transaction(transaction: Transaction) -> bool:
        normalized_action = OptionProcessor._normalize_action(transaction.action_type)
        return (
            normalized_action in OptionProcessingConfig.OPTION_ACTIONS and 
            bool(re.search(OptionProcessingConfig.OPTION_SYMBOL_PATTERN, transaction.symbol or ''))
        )

    def _parse_option_info(self, symbol: str) -> Optional[Dict[str, Any]]:
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
        except Exception as e:
            self.logger.warning(f"オプションシンボルのパースに失敗: {symbol} - {e}")
        return None

    @staticmethod
    def _determine_option_type(action: str) -> str:
        return 'Call' if 'BUY' in action.upper() else 'Put'

    @staticmethod
    def _determine_position_type(action: str) -> str:
        if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE']:
            return OptionProcessingConfig.POSITION_TYPES['LONG']
        return OptionProcessingConfig.POSITION_TYPES['SHORT']

    def _update_summary_record(self, symbol: str, trade_record: OptionTradeRecord, option_info: Dict[str, Any]) -> None:
        if symbol not in self._summary_records:
            self._summary_records[symbol] = OptionSummaryRecord(
                account_id=trade_record.account_id,
                symbol=symbol,
                description=trade_record.description,
                underlying=option_info['underlying'],
                option_type=option_info['option_type'],
                strike_price=option_info['strike_price'],
                expiry_date=option_info['expiry_date'],
                open_date=trade_record.record_date,
                initial_quantity=trade_record.quantity
            )
        
        summary = self._summary_records[symbol]
        summary.trading_pnl += trade_record.trading_pnl
        summary.premium_pnl += trade_record.premium_pnl
        summary.total_fees += trade_record.fees
        summary.remaining_quantity = self._positions[symbol].get_remaining_quantity()

        if trade_record.is_expired:
            summary.status = 'Expired'
            summary.close_date = trade_record.record_date
        elif trade_record.is_assigned:
            summary.status = 'Assigned'
            summary.close_date = trade_record.record_date
        elif summary.remaining_quantity <= 0:
            summary.status = 'Closed'
            summary.close_date = trade_record.record_date

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        return sorted(
            [r for r in self._summary_records.values() if r is not None],
            key=lambda x: (x.underlying or '', x.expiry_date or date.max, x.strike_price or 0)
        )