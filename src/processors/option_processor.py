from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
from collections import defaultdict
import re

from ..core.transaction import Transaction
from ..exchange.money import Money, Currency
from .base import BaseProcessor
from .option_records import OptionTradeRecord, OptionSummaryRecord
from .option_position import OptionPosition, OptionContract

class OptionProcessor(BaseProcessor):
   SHARES_PER_CONTRACT = 100
   
   def __init__(self):
       super().__init__()
       self._positions: Dict[str, OptionPosition] = defaultdict(OptionPosition)
       self._trade_records: List[OptionTradeRecord] = []
       self._summary_records: Dict[str, OptionSummaryRecord] = {}
       self._daily_transactions: Dict[str, Dict[date, List[Transaction]]] = defaultdict(lambda: defaultdict(list))
       self._transaction_tracking: Dict[str, Dict] = defaultdict(lambda: {
           'open_quantity': Decimal('0'),
           'close_quantity': Decimal('0'),
           'max_status': 'Open'
       })

   def process(self, transaction: Transaction) -> None:
       if not self._is_option_transaction(transaction):
           return
       self._process_transaction(transaction)

   def process_all(self, transactions: List[Transaction]) -> List[OptionTradeRecord]:
       self._track_daily_transactions(transactions)
       self._transaction_tracking.clear()
       
       for symbol, daily_symbol_txs in self._daily_transactions.items():
           sorted_dates = sorted(daily_symbol_txs.keys())
           for transaction_date in sorted_dates:
               transactions_on_date = daily_symbol_txs[transaction_date]
               self._process_daily_transactions(symbol, transactions_on_date)

       return self._trade_records

   def _track_daily_transactions(self, transactions: List[Transaction]) -> None:
       for transaction in transactions:
           if self._is_option_transaction(transaction):
               symbol = transaction.symbol
               self._daily_transactions[symbol][transaction.transaction_date].append(transaction)

   def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
       sorted_transactions = sorted(
           transactions, 
           key=lambda tx: (
               0 if self._normalize_action(tx.action_type).endswith('OPEN') else 1,
               -abs(Decimal(str(tx.quantity or 0)))
           )
       )
       
       tracking = self._transaction_tracking[symbol]
       tracking['open_quantity'] = Decimal('0')
       tracking['close_quantity'] = Decimal('0')
       
       for transaction in sorted_transactions:
           action = self._normalize_action(transaction.action_type)
           quantity = abs(Decimal(str(transaction.quantity or 0)))
           
           if action.endswith('OPEN'):
               tracking['open_quantity'] += quantity
           elif action.endswith('CLOSE'):
               tracking['close_quantity'] += quantity
           
           self.process(transaction)
       
       tracking['max_status'] = 'Closed' if (tracking['close_quantity'] >= tracking['open_quantity'] 
                                           and tracking['open_quantity'] > 0) else 'Open'

   def _process_transaction(self, transaction: Transaction) -> None:
       option_info = self._parse_option_info(transaction.symbol)
       if not option_info:
           return
           
       symbol = transaction.symbol
       action = self._normalize_action(transaction.action_type)
       
       quantity = abs(Decimal(str(transaction.quantity or 0)))
       per_share_price = Decimal(str(transaction.price or 0))
       fees = Decimal(str(transaction.fees or 0))

       position = self._positions[symbol]

       total_price = Decimal('0')
       trading_pnl = Decimal('0')
       premium_pnl = Decimal('0')

       if action in ['BUY_TO_OPEN', 'SELL_TO_OPEN']:
           contract = OptionContract(
               trade_date=transaction.transaction_date,
               quantity=quantity,
               price=per_share_price,
               fees=fees,
               position_type='Long' if action == 'BUY_TO_OPEN' else 'Short',
               option_type=option_info['option_type']
           )
           position.add_contract(contract)
           
           total_price = (-per_share_price if action == 'BUY_TO_OPEN' else per_share_price) * self.SHARES_PER_CONTRACT * quantity

       elif action in ['BUY_TO_CLOSE', 'SELL_TO_CLOSE']:
           pnl = position.close_position(
               transaction.transaction_date,
               quantity,
               per_share_price,
               fees,
               action == 'BUY_TO_CLOSE'
           )
           trading_pnl = pnl['realized_gain']
           
           total_price = (-per_share_price if action == 'BUY_TO_CLOSE' else per_share_price) * self.SHARES_PER_CONTRACT * quantity

       elif action in ['EXPIRED', 'ASSIGNED']:
           pnl = position.handle_expiration(transaction.transaction_date)
           premium_pnl = pnl['premium_pnl']

       price_money = self._create_money(total_price)
       fees_money = self._create_money(fees)
       trading_pnl_money = self._create_money(trading_pnl)
       premium_pnl_money = self._create_money(premium_pnl)

       trade_record = OptionTradeRecord(
           trade_date=transaction.transaction_date,
           account_id=transaction.account_id,
           symbol=symbol,
           description=transaction.description,
           action=action,
           quantity=quantity,
           price=price_money,
           fees=fees_money,
           exchange_rate=Money(1).as_currency(Currency.JPY),
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
       normalized_action = self._normalize_action(transaction.action_type)
       option_actions = {
           'BUY_TO_OPEN', 'SELL_TO_OPEN',
           'BUY_TO_CLOSE', 'SELL_TO_CLOSE',
           'EXPIRED', 'ASSIGNED'
       }
       return (normalized_action in option_actions and 
               self._is_option_symbol(transaction.symbol))

   def _is_option_symbol(self, symbol: str) -> bool:
       if not symbol:
           return False
       option_pattern = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
       return bool(re.search(option_pattern, symbol))

   def _normalize_action(self, action: str) -> str:
       action = action.upper().replace(' TO ', '_TO_')
       return action.replace(' ', '')

   def _parse_option_info(self, symbol: str) -> Optional[Dict]:
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
       return 'Long' if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE'] else 'Short'

   def get_records(self) -> List[OptionTradeRecord]:
       return sorted(self._trade_records, key=lambda x: x.trade_date)

   def get_summary_records(self) -> List[OptionSummaryRecord]:
       summary_records = [
           record for record in self._summary_records.values()
           if record is not None
       ]
       
       return sorted(
           summary_records,
           key=lambda x: (x.underlying or '', x.expiry_date or datetime.min.date(), x.strike_price or 0)
       )

   def _update_summary_record(self, symbol: str,
                            trade_record: OptionTradeRecord,
                            option_info: Dict) -> None:
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
               exchange_rate=Money(1).as_currency(Currency.JPY),
           )
       
       summary = self._summary_records[symbol]
       tracking = self._transaction_tracking[symbol]
       
       summary.remaining_quantity = position.get_remaining_quantity()
       summary.trading_pnl += trade_record.trading_pnl
       summary.premium_pnl += trade_record.premium_pnl
       summary.total_fees += trade_record.fees

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