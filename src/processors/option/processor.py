from typing import Dict, List, Tuple, Optional, Any
from datetime import date, datetime
from decimal import Decimal
import re
import logging

from ...core.tx import Transaction
from ..base.processor import BaseProcessor
from ...exchange.money import Money
from ...exchange.currency import Currency

from .record import OptionTradeRecord, OptionSummaryRecord
from .position import OptionPosition, OptionContract
from .tracker import OptionTransactionTracker
from .config import OptionProcessingConfig

class OptionProcessor(BaseProcessor[OptionTradeRecord, OptionSummaryRecord]):
    """オプション処理クラス"""
    
    def __init__(self) -> None:
        super().__init__()
        self._positions: Dict[str, OptionPosition] = {}
        self._transaction_tracker = OptionTransactionTracker()
        self._record_class = OptionTradeRecord
        self._summary_class = OptionSummaryRecord
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(self, symbol: str, transactions: List[Transaction]) -> None:
        """日次トランザクションの処理"""
        option_transactions = [t for t in transactions if self._is_option_transaction(t)]
        
        if option_transactions:
            sorted_transactions = self._sort_option_transactions(option_transactions)
            for transaction in sorted_transactions:
                self.process(transaction)

    def _sort_option_transactions(self, transactions: List[Transaction]) -> List[Transaction]:
        """オプショントランザクションのソート"""
        return sorted(
            transactions, 
            key=lambda tx: (
                0 if self._normalize_action(tx.action_type).endswith('OPEN') else 1,
                -abs(Decimal(str(tx.quantity or 0)))
            )
        )

    def process(self, transaction: Transaction) -> None:
        """オプショントランザクションの処理"""
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
        """オプション取引の実際の処理"""
        try:
            # 基本情報の取得
            trade_info = self._extract_trade_info(transaction)
            
            # ポジション更新と取引結果の取得
            position = self._get_or_create_position(transaction.symbol)
            trading_result = self._handle_transaction_type(position, trade_info)
            
            # Money オブジェクトの作成
            money_values = self._create_money_values(trade_info, trading_result, transaction.transaction_date)
            
            # 取引レコードの作成
            record = self._create_trade_record(
                record_date=transaction.transaction_date,
                account_id=transaction.account_id,
                symbol=transaction.symbol,
                description=transaction.description,
                **self._create_record_params(trade_info, option_info, money_values, position)
            )
            
            # レコードの保存と更新
            self._save_and_update_records(record, position, option_info)
            
            # トラッキング情報の更新
            self._update_tracking(transaction.symbol, trade_info, trading_result)

        except Exception as e:
            self.logger.error(f"オプション取引処理中にエラー: {e}")
            raise

    def _extract_trade_info(self, transaction: Transaction) -> Dict[str, Any]:
        """取引情報の抽出"""
        return {
            'action': self._normalize_action(transaction.action_type),
            'quantity': abs(Decimal(str(transaction.quantity or 0))),
            'price': Decimal(str(transaction.price or 0)),
            'fees': Decimal(str(transaction.fees or 0))
        }

    def _handle_transaction_type(
        self, 
        position: OptionPosition, 
        trade_info: Dict[str, Any]
    ) -> Dict[str, Decimal]:
        """取引タイプに応じた処理"""
        total_price = Decimal('0')
        trading_pnl = Decimal('0')
        premium_pnl = Decimal('0')

        if trade_info['action'] in OptionProcessingConfig.ACTION_TYPES['OPEN']:
            total_price = self._handle_open_position(position, trade_info)
        elif trade_info['action'] in OptionProcessingConfig.ACTION_TYPES['CLOSE']:
            trading_pnl, total_price = self._handle_close_position(position, trade_info)
        elif trade_info['action'] in ['EXPIRED', 'ASSIGNED']:
            premium_pnl = self._handle_expiration(position, trade_info)

        return {
            'total_price': total_price,
            'trading_pnl': trading_pnl,
            'premium_pnl': premium_pnl
        }

    def _handle_open_position(self, position: OptionPosition, trade_info: Dict[str, Any]) -> Decimal:
        """オープンポジションの処理"""
        is_buy = trade_info['action'] == 'BUY_TO_OPEN'
        contract = OptionContract(
            trade_date=date.today(),
            quantity=trade_info['quantity'],
            price=trade_info['price'],
            fees=trade_info['fees'],
            position_type=OptionProcessingConfig.POSITION_TYPES['LONG' if is_buy else 'SHORT'],
            option_type=self._determine_option_type(trade_info['action'])
        )
        position.add_contract(contract)
        return (-trade_info['price'] if is_buy else trade_info['price']) * trade_info['quantity'] * 100

    def _handle_close_position(
        self, 
        position: OptionPosition, 
        trade_info: Dict[str, Any]
    ) -> Tuple[Decimal, Decimal]:
        """クローズポジションの処理"""
        is_buy = trade_info['action'] == 'BUY_TO_CLOSE'
        pnl = position.close_position(
            date.today(),
            trade_info['quantity'],
            trade_info['price'],
            trade_info['fees'],
            is_buy
        )
        total_price = (-trade_info['price'] if is_buy else trade_info['price']) * trade_info['quantity'] * 100
        return pnl['realized_gain'], total_price

    def _handle_expiration(self, position: OptionPosition, trade_info: Dict[str, Any]) -> Decimal:
        """満期処理"""
        pnl = position.handle_expiration(date.today())
        return pnl['premium_pnl']

    def _create_money_values(
        self, 
        trade_info: Dict[str, Any], 
        trading_result: Dict[str, Decimal],
        transaction_date: date
    ) -> Dict[str, Money]:
        """Money オブジェクトの作成"""
        return {
            'price': self._create_money(trade_info['price'] * trade_info['quantity'], transaction_date),
            'fees': self._create_money(trade_info['fees'], transaction_date),
            'trading_pnl': self._create_money(trading_result.get('trading_pnl', 0), transaction_date),
            'premium_pnl': self._create_money(trading_result.get('premium_pnl', 0), transaction_date)
        }

    def _create_record_params(
        self,
        trade_info: Dict[str, Any],
        option_info: Dict[str, Any],
        money_values: Dict[str, Money],
        position: OptionPosition
    ) -> Dict[str, Any]:
        """レコードパラメータの作成"""
        return {
            'action': trade_info['action'],
            'quantity': trade_info['quantity'],
            'option_type': option_info['option_type'],
            'strike_price': option_info['strike_price'],
            'expiry_date': option_info['expiry_date'],
            'underlying': option_info['underlying'],
            'price': money_values['price'],
            'fees': money_values['fees'],
            'trading_pnl': money_values['trading_pnl'],
            'premium_pnl': money_values['premium_pnl'],
            'exchange_rate': money_values['price'].get_rate(),
            'position_type': self._determine_position_type(trade_info['action']),
            'is_closed': not position.has_open_position(),
            'is_expired': trade_info['action'] == 'EXPIRED',
            'is_assigned': trade_info['action'] == 'ASSIGNED'
        }

    def _update_tracking(
        self,
        symbol: str,
        trade_info: Dict[str, Any],
        trading_result: Dict[str, Decimal]
    ) -> None:
        """トラッキング情報の更新"""
        self._transaction_tracker.update_tracking(
            symbol, 
            trade_info['action'],
            trade_info['quantity'],
            {
                'trading_pnl': trading_result.get('trading_pnl', 0),
                'premium_pnl': trading_result.get('premium_pnl', 0)
            }
        )

    def _save_and_update_records(
        self,
        record: OptionTradeRecord,
        position: OptionPosition,
        option_info: Dict[str, Any]
    ) -> None:
        """レコードの保存と更新"""
        self._trade_records.append(record)
        self._update_summary_record(record.symbol, record, option_info)

    @staticmethod
    def _normalize_action(action: str) -> str:
        """アクション名の正規化"""
        return action.upper().replace(' TO ', '_TO_').replace(' ', '')

    @staticmethod
    def _is_option_transaction(transaction: Transaction) -> bool:
        """オプション取引の判定"""
        normalized_action = OptionProcessor._normalize_action(transaction.action_type)
        return (
            normalized_action in OptionProcessingConfig.OPTION_ACTIONS and 
            bool(re.search(OptionProcessingConfig.OPTION_SYMBOL_PATTERN, transaction.symbol or ''))
        )

    def _parse_option_info(self, symbol: str) -> Optional[Dict[str, Any]]:
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
        except Exception as e:
            self.logger.warning(f"オプションシンボルのパースに失敗: {symbol} - {e}")
        return None

    def _get_or_create_position(self, symbol: str) -> OptionPosition:
        """ポジションの取得または作成"""
        if symbol not in self._positions:
            self._positions[symbol] = OptionPosition()
        return self._positions[symbol]

    @staticmethod
    def _determine_option_type(action: str) -> str:
        """オプションタイプの判定"""
        return 'Call' if 'BUY' in action.upper() else 'Put'

    @staticmethod
    def _determine_position_type(action: str) -> str:
        """ポジションタイプの判定"""
        if action in ['BUY_TO_OPEN', 'SELL_TO_CLOSE']:
            return OptionProcessingConfig.POSITION_TYPES['LONG']
        return OptionProcessingConfig.POSITION_TYPES['SHORT']

    def _update_summary_record(
        self,
        symbol: str,
        trade_record: OptionTradeRecord,
        option_info: Dict[str, Any]
    ) -> None:
        """サマリーレコードの更新"""
        if symbol not in self._summary_records:
            self._summary_records[symbol] = self._create_summary_record(
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
        """サマリーレコードの取得"""
        return sorted(
            [r for r in self._summary_records.values() if r is not None],
            key=lambda x: (x.underlying or '', x.expiry_date or date.max, x.strike_price or 0)
        )