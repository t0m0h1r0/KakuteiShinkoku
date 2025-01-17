from decimal import Decimal
from typing import Dict, Optional
from datetime import date

from .base import BaseProcessor
from ..core.models import Transaction, DividendRecord, Money
from ..config.constants import CDConstants, Currency
from ..config.action_types import ActionTypes

class CDProcessor(BaseProcessor[DividendRecord]):
    """CD（譲渡性預金）処理クラス"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cd_positions: Dict[str, Money] = {}  # symbol -> principal amount

    def _is_target_transaction(self, transaction: Transaction) -> bool:
        """CD関連のトランザクションかどうかを判定"""
        return (self._is_cd_purchase(transaction) or 
                transaction.action_type == CDConstants.INTEREST_ACTION)

    def _process_transaction(self, transaction: Transaction) -> None:
        """CDトランザクションを処理"""
        try:
            if self._is_cd_purchase(transaction):
                self._process_cd_purchase(transaction)
            elif transaction.action_type == CDConstants.INTEREST_ACTION:
                self._process_cd_interest(transaction)
        except Exception as e:
            self._logger.error(f"CD transaction processing error: {e}", exc_info=True)
            raise

    def _is_cd_purchase(self, transaction: Transaction) -> bool:
        """CD購入トランザクションかどうかを判定"""
        return (transaction.amount < 0 and
                any(keyword in transaction.description 
                    for keyword in CDConstants.PURCHASE_KEYWORDS))

    def _process_cd_purchase(self, transaction: Transaction) -> None:
        """CD購入を処理"""
        principal = abs(transaction.amount)
        self._cd_positions[transaction.symbol] = Money(principal)
        self._logger.info(f"Recorded CD purchase: {transaction.symbol}, "
                         f"Principal: {principal}")

    def _process_cd_interest(self, transaction: Transaction) -> None:
        """CD利子を処理"""
        principal = self._cd_positions.get(
            transaction.symbol,
            Money(Decimal('0'))
        )

        record = DividendRecord(
            record_date=transaction.transaction_date,
            account_id=transaction.account_id,
            symbol=transaction.symbol,
            description=transaction.description,
            income_type=CDConstants.INTEREST_ACTION,
            gross_amount=Money(transaction.amount),
            tax_amount=Money(Decimal('0')),
            exchange_rate=self._get_exchange_rate(transaction.transaction_date),
            is_reinvested=False,
            principal_amount=principal
        )

        self.records.append(record)
        self._logger.info(f"Recorded CD interest: {transaction.symbol}, "
                         f"Interest: {transaction.amount}")
