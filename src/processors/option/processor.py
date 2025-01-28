from typing import Dict, List, Optional
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


class OptionProcessor(BaseProcessor[OptionTradeRecord]):
    def __init__(self):
        super().__init__()
        self._positions: Dict[str, OptionPosition] = {}
        self._summary_records: Dict[str, OptionSummaryRecord] = {}
        self._transaction_tracker = OptionTransactionTracker()
        self.logger = logging.getLogger(self.__class__.__name__)

    def _process_daily_transactions(
        self, symbol: str, transactions: List[Transaction]
    ) -> None:
        """日次トランザクションを処理"""
        # オプション取引のみフィルタリング
        option_transactions = [
            t for t in transactions if self._is_option_transaction(t)
        ]

        if option_transactions:
            # アクションタイプでソート
            sorted_transactions = sorted(
                option_transactions,
                key=lambda tx: (
                    0 if self._normalize_action(tx.action_type).endswith("OPEN") else 1,
                    -abs(Decimal(str(tx.quantity or 0))),
                ),
            )

            for transaction in sorted_transactions:
                self._process_transaction(transaction)

    def process(self, transaction: Transaction) -> None:
        """単一トランザクションを処理"""
        try:
            if self._is_option_transaction(transaction):
                self._process_transaction(transaction)
        except Exception as e:
            self.logger.error(f"オプション取引の処理中にエラー: {transaction} - {e}")

    def _process_transaction(self, transaction: Transaction) -> None:
        """オプション取引の処理"""
        option_info = self._parse_option_info(transaction.symbol)
        if not option_info:
            return

        symbol = transaction.symbol
        action = self._normalize_action(transaction.action_type)
        quantity = abs(Decimal(str(transaction.quantity or 0)))
        per_share_price = Decimal(str(transaction.price or 0))
        fees = Decimal(str(transaction.fees or 0))

        position = self._get_or_create_position(symbol)
        trading_result = self._handle_transaction_type(
            position,
            action,
            quantity,
            per_share_price,
            fees,
            transaction.transaction_date,
        )

        # Money オブジェクトの作成
        price_money = Money(
            per_share_price * quantity, Currency.USD, transaction.transaction_date
        )
        fees_money = Money(fees, Currency.USD, transaction.transaction_date)
        trading_pnl_money = Money(
            trading_result.get("trading_pnl", 0),
            Currency.USD,
            transaction.transaction_date,
        )
        premium_pnl_money = Money(
            trading_result.get("premium_pnl", 0),
            Currency.USD,
            transaction.transaction_date,
        )

        trade_record = OptionTradeRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=symbol,
            description=transaction.description,
            action=action,
            quantity=quantity,
            option_type=option_info["option_type"],
            strike_price=option_info["strike_price"],
            expiry_date=option_info["expiry_date"],
            underlying=option_info["underlying"],
            price=price_money,
            fees=fees_money,
            trading_pnl=trading_pnl_money,
            premium_pnl=premium_pnl_money,
            exchange_rate=price_money.get_rate(),
            position_type=self._determine_position_type(action),
            is_closed=not position.has_open_position(),
            is_expired=(action == "EXPIRED"),
            is_assigned=(action == "ASSIGNED"),
        )

        self._trade_records.append(trade_record)
        self._update_summary_record(symbol, trade_record, option_info)

        self._transaction_tracker.update_tracking(
            symbol,
            action,
            quantity,
            {
                "trading_pnl": trading_result.get("trading_pnl", 0),
                "premium_pnl": trading_result.get("premium_pnl", 0),
            },
        )

    def _get_or_create_position(self, symbol: str) -> OptionPosition:
        """シンボルに対するポジションを取得または作成"""
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
        trade_date: date,
    ) -> Dict:
        """取引タイプに応じた処理"""
        total_price = Decimal("0")
        trading_pnl = Decimal("0")
        premium_pnl = Decimal("0")

        if action in OptionProcessingConfig.ACTION_TYPES["OPEN"]:
            contract = OptionContract(
                trade_date=trade_date,
                quantity=quantity,
                price=per_share_price,
                fees=fees,
                position_type=OptionProcessingConfig.POSITION_TYPES[
                    "LONG" if action == "BUY_TO_OPEN" else "SHORT"
                ],
                option_type=self._determine_option_type(action),
            )
            position.add_contract(contract)

            total_price = (
                (-per_share_price if action == "BUY_TO_OPEN" else per_share_price)
                * OptionProcessingConfig.SHARES_PER_CONTRACT
                * quantity
            )

        elif action in OptionProcessingConfig.ACTION_TYPES["CLOSE"]:
            pnl = position.close_position(
                trade_date, quantity, per_share_price, fees, action == "BUY_TO_CLOSE"
            )
            trading_pnl = pnl["realized_gain"]

            total_price = (
                (-per_share_price if action == "BUY_TO_CLOSE" else per_share_price)
                * OptionProcessingConfig.SHARES_PER_CONTRACT
                * quantity
            )

        elif action in ["EXPIRED", "ASSIGNED"]:
            pnl = position.handle_expiration(trade_date)
            premium_pnl = pnl["premium_pnl"]

        return {
            "total_price": total_price,
            "trading_pnl": trading_pnl,
            "premium_pnl": premium_pnl,
        }

    @staticmethod
    def _normalize_action(action: str) -> str:
        """アクション名の正規化"""
        return action.upper().replace(" TO ", "_TO_").replace(" ", "")

    @staticmethod
    def _is_option_transaction(transaction: Transaction) -> bool:
        """オプション取引の判定"""
        normalized_action = OptionProcessor._normalize_action(transaction.action_type)
        return normalized_action in OptionProcessingConfig.OPTION_ACTIONS and bool(
            re.search(
                OptionProcessingConfig.OPTION_SYMBOL_PATTERN, transaction.symbol or ""
            )
        )

    def _parse_option_info(self, symbol: str) -> Optional[Dict]:
        """オプション情報のパース"""
        try:
            pattern = r"(\w+)\s+(\d{2}/\d{2}/\d{4})\s+(\d+\.\d+)\s+([CP])"
            match = re.match(pattern, symbol)
            if match:
                underlying, expiry, strike, option_type = match.groups()
                return {
                    "underlying": underlying,
                    "expiry_date": datetime.strptime(expiry, "%m/%d/%Y").date(),
                    "strike_price": Decimal(strike),
                    "option_type": "Call" if option_type == "C" else "Put",
                }
        except Exception as e:
            self.logger.warning(f"オプションシンボルのパースに失敗: {symbol} - {e}")
        return None

    @staticmethod
    def _determine_option_type(action: str) -> str:
        """オプションタイプの決定"""
        return "Call" if "BUY" in action.upper() else "Put"

    @staticmethod
    def _determine_position_type(action: str) -> str:
        """ポジションタイプの決定"""
        if action in ["BUY_TO_OPEN", "SELL_TO_CLOSE"]:
            return OptionProcessingConfig.POSITION_TYPES["LONG"]
        return OptionProcessingConfig.POSITION_TYPES["SHORT"]

    def _update_summary_record(
        self, symbol: str, trade_record: OptionTradeRecord, option_info: Dict
    ) -> None:
        """サマリーレコードの更新"""
        position = self._positions[symbol]

        if symbol not in self._summary_records:
            self._summary_records[symbol] = self._create_summary_record(
                trade_record, option_info
            )

        summary = self._summary_records[symbol]
        self._update_summary_values(summary, position, trade_record)

    def _create_summary_record(
        self, trade_record: OptionTradeRecord, option_info: Dict
    ) -> OptionSummaryRecord:
        """サマリーレコードの作成"""
        return OptionSummaryRecord(
            account_id=trade_record.account_id,
            symbol=trade_record.symbol,
            description=trade_record.description,
            underlying=option_info["underlying"],
            option_type=option_info["option_type"],
            strike_price=option_info["strike_price"],
            expiry_date=option_info["expiry_date"],
            open_date=trade_record.record_date,
            initial_quantity=trade_record.quantity,
            trading_pnl=trade_record.trading_pnl,
            premium_pnl=trade_record.premium_pnl,
            total_fees=trade_record.fees,
        )

    def _update_summary_values(
        self,
        summary: OptionSummaryRecord,
        position: OptionPosition,
        trade_record: OptionTradeRecord,
    ) -> None:
        """サマリー値の更新"""
        summary.remaining_quantity = position.get_remaining_quantity()
        summary.trading_pnl += trade_record.trading_pnl
        summary.premium_pnl += trade_record.premium_pnl
        summary.total_fees += trade_record.fees

        if trade_record.is_expired:
            summary.status = "Expired"
            summary.close_date = trade_record.record_date
        elif trade_record.is_assigned:
            summary.status = "Assigned"
            summary.close_date = trade_record.record_date
        elif summary.remaining_quantity <= 0:
            summary.status = "Closed"
            summary.close_date = trade_record.record_date

    def get_summary_records(self) -> List[OptionSummaryRecord]:
        """サマリーレコードの取得"""
        return sorted(
            [r for r in self._summary_records.values() if r is not None],
            key=lambda x: (
                x.underlying or "",
                x.expiry_date or date.max,
                x.strike_price or 0,
            ),
        )
