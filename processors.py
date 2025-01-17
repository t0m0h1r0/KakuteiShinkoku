from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import json
import logging
import re

from config import (
    CSV_ENCODING, DIVIDEND_ACTIONS, TAX_ACTIONS, DATE_FORMAT,
    CD_MATURITY_ACTION, CD_ADJUSTMENT_ACTION, CD_INTEREST_ACTION,
    CD_PURCHASE_KEYWORDS, CD_MATURED_KEYWORD
)
from models import Transaction, DividendRecord
from exchange_rates import ExchangeRateManager

class TransactionProcessor:
    """取引データの処理を行うクラス"""

    def __init__(self, exchange_rate_manager: ExchangeRateManager):
        self.exchange_rate_manager = exchange_rate_manager

    def load_transactions(self, filename: Path) -> List[Transaction]:
        """JSONファイルから取引データを読み込む"""
        try:
            with filename.open('r', encoding=CSV_ENCODING) as f:
                data = json.load(f)
                return [
                    self._create_transaction(trans, filename.stem)
                    for trans in data['BrokerageTransactions']
                ]
        except Exception as e:
            logging.error(f"ファイル {filename} の読み込み中にエラー: {e}")
            return []

    def _create_transaction(self, trans_data: Dict, account: str) -> Transaction:
        """取引データからTransactionオブジェクトを作成"""
        return Transaction(
            date=trans_data['Date'].split(' as of ')[0],
            account=account,
            symbol=trans_data.get('Symbol', ''),
            description=trans_data['Description'],
            amount=self._parse_amount(trans_data['Amount']),
            action=trans_data['Action']
        )

    @staticmethod
    def _parse_amount(amount_str: Optional[str]) -> Decimal:
        """金額文字列をDecimal型に変換"""
        if not amount_str:
            return Decimal('0')
        return Decimal(amount_str.replace('$', '').replace(',', ''))

    def process_transactions(self, transactions: List[Transaction]) -> List[DividendRecord]:
        """取引データを処理し配当記録を生成"""
        record_dict: Dict[Tuple[str, str, str], Dict] = {}
        
        for trans in transactions:
            if not self._is_relevant_transaction(trans):
                continue

            key = (trans.date, trans.symbol or trans.description, trans.account)
            
            if key not in record_dict:
                record_dict[key] = {
                    'date': trans.date,
                    'account': trans.account,
                    'symbol': trans.symbol,
                    'description': trans.description,
                    'type': 'Interest' if any(word in trans.action for word in ['Interest', 'Bank']) else 'Dividend',
                    'gross_amount': Decimal('0'),
                    'tax': Decimal('0'),
                    'exchange_rate': self.exchange_rate_manager.get_rate(trans.date),
                    'reinvested': False,
                    'principal': Decimal('0')
                }
            
            self._update_record_dict(record_dict[key], trans)
        
        dividend_records = [
            DividendRecord(**record_data)
            for record_data in record_dict.values()
            if record_data['gross_amount'] > 0 or record_data['tax'] > 0
        ]
        
        return sorted(
            dividend_records,
            key=lambda x: datetime.strptime(x.date, DATE_FORMAT)
        )

    @staticmethod
    def _is_relevant_transaction(trans: Transaction) -> bool:
        """処理対象となる取引かどうかを判定"""
        return (trans.action in DIVIDEND_ACTIONS or
                (trans.action in TAX_ACTIONS and trans.amount < 0))

    def _update_record_dict(self, record_data: Dict, trans: Transaction) -> None:
        """記録データを更新"""
        if trans.action in TAX_ACTIONS:
            record_data['tax'] = abs(trans.amount)
        else:
            record_data['gross_amount'] = trans.amount
            if trans.action == 'Reinvest Dividend':
                record_data['reinvested'] = True


class CDProcessor:
    """CD取引データの処理を行うクラス"""

    def __init__(self, exchange_rate_manager: ExchangeRateManager):
        self.exchange_rate_manager = exchange_rate_manager
        self._cd_records: Dict[str, DividendRecord] = {}
        self._principals: Dict[str, Decimal] = {}  # CDのシンボルごとの元本を保存

    def process_transaction(self, trans: Transaction) -> None:
        """CD取引を処理"""
        if self._is_cd_purchase(trans):
            self._process_cd_purchase(trans)
        elif trans.action == CD_INTEREST_ACTION:
            self._process_cd_interest(trans)

    def get_interest_records(self) -> List[DividendRecord]:
        """処理済みのCD取引から利子記録を生成"""
        return sorted(
            self._cd_records.values(),
            key=lambda x: datetime.strptime(x.date, DATE_FORMAT)
        )

    def _is_cd_purchase(self, trans: Transaction) -> bool:
        """CD購入取引かどうかを判定"""
        return (trans.amount < 0 and
                any(keyword in trans.description 
                    for keyword in CD_PURCHASE_KEYWORDS))

    def _process_cd_purchase(self, trans: Transaction) -> None:
        """CD購入取引を処理"""
        try:
            self._principals[trans.symbol] = abs(trans.amount)
            logging.info(f"CD purchase recorded: {trans.symbol}, Principal: {abs(trans.amount)}")
        except Exception as e:
            logging.error(f"CD購入取引の処理中にエラー: {e}, 取引: {trans}")

    def _process_cd_interest(self, trans: Transaction) -> None:
        """CD利子取引を処理"""
        try:
            principal = self._principals.get(trans.symbol, Decimal('0'))
            
            record = DividendRecord(
                date=trans.date,
                account=trans.account,
                symbol=trans.symbol,
                description=trans.description,
                type='CD Interest',
                gross_amount=trans.amount,
                tax=Decimal('0'),
                exchange_rate=self.exchange_rate_manager.get_rate(trans.date),
                reinvested=False,
                principal=principal
            )
            
            self._cd_records[trans.symbol] = record
            logging.info(f"CD interest recorded: {trans.symbol}, Interest: {trans.amount}")

        except Exception as e:
            logging.error(f"CD利子取引の処理中にエラー: {e}, 取引: {trans}")