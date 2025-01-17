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
    CD_PURCHASE_KEYWORDS, CD_MATURED_KEYWORD, OPTION_ACTIONS,
    STOCK_ACTIONS, OPTION_TYPE_CALL, OPTION_TYPE_PUT,
    OPTION_SYMBOL_REGEX
)
from models import (
    Transaction, DividendRecord, TradeRecord,
    Position, OptionContract
)
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
            action=trans_data['Action'],
            quantity=self._parse_amount(trans_data.get('Quantity', '')),
            price=self._parse_amount(trans_data.get('Price', '')),
            fees=self._parse_amount(trans_data.get('Fees & Comm', ''))
        )

    @staticmethod
    def _parse_amount(amount_str: Optional[str]) -> Decimal:
        """金額文字列をDecimal型に変換"""
        if not amount_str or amount_str == '':
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


class TradeProcessor:
    """取引損益の処理を行うクラス"""

    def __init__(self, exchange_rate_manager: ExchangeRateManager):
        self.exchange_rate_manager = exchange_rate_manager
        self._stock_positions: Dict[str, Position] = {}  # symbol -> Position
        self._option_positions: Dict[str, Position] = {} # full_symbol -> Position
        self._trade_records: List[TradeRecord] = []

    def process_transaction(self, trans: Transaction) -> None:
        """取引を処理"""
        try:
            if trans.action in OPTION_ACTIONS:
                self._process_option_trade(trans)
            elif trans.action in STOCK_ACTIONS:
                self._process_stock_trade(trans)
        except Exception as e:
            logging.error(f"取引処理中にエラー: {e}, 取引: {trans}")

    def get_trade_records(self) -> List[TradeRecord]:
        """処理済みの取引記録を取得"""
        return sorted(
            self._trade_records,
            key=lambda x: datetime.strptime(x.date, DATE_FORMAT)
        )

    def _process_option_trade(self, trans: Transaction) -> None:
        """オプション取引を処理"""
        try:
            contract = self._parse_option_contract(trans.symbol, trans.description)
            if not contract:
                logging.warning(f"オプション契約の解析に失敗: {trans.symbol}")
                return

            if trans.action == 'Expired':
                self._handle_option_expiration(contract)
            elif trans.action == 'Assigned':
                self._handle_option_assignment(trans, contract)
            else:
                self._handle_option_trade(trans, contract)

        except Exception as e:
            logging.error(f"オプション取引の処理中にエラー: {e}, 取引: {trans}")

    def _process_stock_trade(self, trans: Transaction) -> None:
        """株式取引を処理"""
        try:
            if not trans.quantity or not trans.price:
                logging.warning(f"株式取引: 数量または価格が不足しています: {trans}")
                return

            quantity = Decimal(str(trans.quantity))
            price = Decimal(str(trans.price))
            fees = trans.fees if trans.fees else Decimal('0')
            
            if trans.action == 'Buy':
                self._handle_stock_purchase(trans.symbol, quantity, price, fees)
            elif trans.action == 'Sell':
                self._handle_stock_sale(trans, quantity, price, fees)

        except Exception as e:
            logging.error(f"株式取引の処理中にエラー: {e}, 取引: {trans}")

    def _parse_option_contract(self, symbol: str, description: str) -> Optional[OptionContract]:
        """オプションシンボルをパース"""
        try:
            # シンボルから直接情報を抽出
            parts = symbol.split()
            if len(parts) != 4:  # 例: "RBLX 09/01/2023 25.00 P"
                return None
                
            underlying = parts[0]
            expiry = parts[1]
            strike = Decimal(parts[2])
            opt_type = parts[3]
            
            return OptionContract(
                underlying=underlying,
                expiry=expiry,
                strike=strike,
                type=opt_type
            )

        except Exception as e:
            logging.error(f"オプションシンボルのパース中にエラー: {e}, シンボル: {symbol}")
            return None

    def _handle_stock_purchase(self, symbol: str, quantity: Decimal, price: Decimal, fees: Decimal) -> None:
        """株式購入を処理"""
        cost = quantity * price + fees
        if symbol not in self._stock_positions:
            self._stock_positions[symbol] = Position(symbol, quantity, cost)
        else:
            pos = self._stock_positions[symbol]
            self._stock_positions[symbol] = Position(
                symbol,
                pos.quantity + quantity,
                pos.cost_basis + cost
            )
        logging.info(f"株式購入を記録: {symbol}, 数量: {quantity}, コスト: {cost}")

    def _handle_stock_sale(self, trans: Transaction, quantity: Decimal, price: Decimal, fees: Decimal) -> None:
        """株式売却を処理"""
        if trans.symbol not in self._stock_positions:
            logging.warning(f"ポジションが見つかりません: {trans.symbol}")
            return

        pos = self._stock_positions[trans.symbol]
        if pos.quantity < quantity:
            logging.error(f"売却数量がポジションを超えています: {trans.symbol}")
            return

        proceeds = quantity * price - fees
        avg_cost = pos.average_cost
        realized_gain = proceeds - (quantity * avg_cost)

        # ポジション更新
        remaining_quantity = pos.quantity - quantity
        remaining_cost = pos.cost_basis * (remaining_quantity / pos.quantity)
        
        if remaining_quantity > 0:
            self._stock_positions[trans.symbol] = Position(
                trans.symbol, remaining_quantity, remaining_cost
            )
        else:
            del self._stock_positions[trans.symbol]

        # 取引記録作成
        self._trade_records.append(TradeRecord(
            date=trans.date,
            account=trans.account,
            symbol=trans.symbol,
            description=trans.description,
            type='Stock',
            action=trans.action,
            quantity=quantity,
            price=price,
            fees=fees,
            realized_gain=realized_gain,
            cost_basis=quantity * avg_cost,
            proceeds=proceeds,
            exchange_rate=self.exchange_rate_manager.get_rate(trans.date)
        ))
        logging.info(f"株式売却を記録: {trans.symbol}, 数量: {quantity}, 利益: {realized_gain}")

    def _handle_option_trade(self, trans: Transaction, contract: OptionContract) -> None:
        """オプション取引を処理（売買）"""
        if not trans.quantity or not trans.price:
            logging.warning(f"オプション取引: 数量または価格が不足しています: {trans}")
            return

        quantity = Decimal(str(trans.quantity))
        price = Decimal(str(trans.price))
        fees = trans.fees if trans.fees else Decimal('0')
        
        if trans.action in ['Sell to Open', 'Buy to Open']:
            self._handle_option_open(trans, contract, quantity, price, fees)
        else:  # Sell to Close, Buy to Close
            self._handle_option_close(trans, contract, quantity, price, fees)

    def _handle_option_open(self, trans: Transaction, contract: OptionContract, quantity: Decimal, price: Decimal, fees: Decimal) -> None:
        """オプションの新規建て処理"""
        try:
            if trans.action == 'Sell to Open':
                # プレミアム収入として記録
                self._trade_records.append(TradeRecord(
                    date=trans.date,
                    account=trans.account,
                    symbol=contract.full_symbol,
                    description=trans.description,
                    type='Option Premium',
                    action=trans.action,
                    quantity=quantity,
                    price=price,
                    fees=fees,
                    realized_gain=abs(trans.amount) - fees,  # 実際の取引金額を使用
                    cost_basis=Decimal('0'),
                    proceeds=abs(trans.amount),
                    exchange_rate=self.exchange_rate_manager.get_rate(trans.date)
                ))
                logging.info(f"オプションプレミアム収入を記録: {trans.symbol}, 収入: {abs(trans.amount)}")
            else:  # Buy to Open
                cost = quantity * price * Decimal('100') + fees
                if contract.full_symbol not in self._option_positions:
                    self._option_positions[contract.full_symbol] = Position(
                        contract.full_symbol, quantity, cost)
                else:
                    pos = self._option_positions[contract.full_symbol]
                    self._option_positions[contract.full_symbol] = Position(
                        contract.full_symbol,
                        pos.quantity + quantity,
                        pos.cost_basis + cost
                    )
                logging.info(f"オプション購入を記録: {trans.symbol}, コスト: {cost}")
        except Exception as e:
            logging.error(f"オプション新規建ての処理中にエラー: {e}, 取引: {trans}")

    def _handle_option_close(self, trans: Transaction, contract: OptionContract, quantity: Decimal, price: Decimal, fees: Decimal) -> None:
        """オプションの決済処理"""
        if contract.full_symbol not in self._option_positions:
            logging.warning(f"オプションポジションが見つかりません: {contract.full_symbol}")
            return

        pos = self._option_positions[contract.full_symbol]
        if pos.quantity < quantity:
            logging.error(f"決済数量がポジションを超えています: {contract.full_symbol}")
            return

        proceeds = quantity * price * Decimal('100') - fees
        avg_cost = pos.average_cost
        realized_gain = proceeds - (quantity * avg_cost / pos.quantity)

        # ポジション更新
        remaining_quantity = pos.quantity - quantity
        remaining_cost = pos.cost_basis * (remaining_quantity / pos.quantity)
        
        if remaining_quantity > 0:
            self._option_positions[contract.full_symbol] = Position(
                contract.full_symbol, remaining_quantity, remaining_cost
            )
        else:
            del self._option_positions[contract.full_symbol]

        # 取引記録作成
        self._trade_records.append(TradeRecord(
            date=trans.date,
            account=trans.account,
            symbol=contract.full_symbol,
            description=trans.description,
            type='Option',
            action=trans.action,
            quantity=quantity,
            price=price,
            fees=fees,
            realized_gain=realized_gain,
            cost_basis=quantity * avg_cost / pos.quantity,
            proceeds=proceeds,
            exchange_rate=self.exchange_rate_manager.get_rate(trans.date)
        ))
        logging.info(f"オプション決済を記録: {contract.full_symbol}, 利益: {realized_gain}")

    def _handle_option_expiration(self, contract: OptionContract) -> None:
        """オプションの満期失効処理"""
        try:
            if contract.full_symbol not in self._option_positions:
                return

            pos = self._option_positions[contract.full_symbol]
            realized_gain = -pos.cost_basis  # 投資額全額が損失

            # 取引記録作成
            self._trade_records.append(TradeRecord(
                date=contract.expiry,
                account='',  # トランザクションから取得できない
                symbol=contract.full_symbol,
                description=f"Option Expired - {contract.full_symbol}",
                type='Option',
                action='Expired',
                quantity=pos.quantity,
                price=Decimal('0'),
                fees=Decimal('0'),
                realized_gain=realized_gain,
                cost_basis=pos.cost_basis,
                proceeds=Decimal('0'),
                exchange_rate=self.exchange_rate_manager.get_rate(contract.expiry)
            ))
            logging.info(f"オプション満期失効を記録: {contract.full_symbol}, 損失: {realized_gain}")

            # ポジション削除
            del self._option_positions[contract.full_symbol]
        except Exception as e:
            logging.error(f"オプション満期失効の処理中にエラー: {e}, コントラクト: {contract}")

    def _handle_option_assignment(self, trans: Transaction, contract: OptionContract) -> None:
        """オプションの権利行使/割当処理"""
        if contract.full_symbol not in self._option_positions:
            return

        pos = self._option_positions[contract.full_symbol]
        realized_gain = -pos.cost_basis  # オプションのコストベースを損失として記録

        # 取引記録作成
        self._trade_records.append(TradeRecord(
            date=trans.date,
            account=trans.account,
            symbol=contract.full_symbol,
            description=trans.description,
            type='Option',
            action='Assigned',
            quantity=pos.quantity,
            price=contract.strike,
            fees=Decimal('0'),
            realized_gain=realized_gain,
            cost_basis=pos.cost_basis,
            proceeds=Decimal('0'),
            exchange_rate=self.exchange_rate_manager.get_rate(trans.date)
        ))

        # 対応する株式ポジションの調整
        if contract.type == OPTION_TYPE_CALL:
            # コールの場合は保有株を売却
            self._handle_stock_sale(
                trans,
                pos.quantity * Decimal('100'),
                contract.strike,
                Decimal('0')
            )
        else:  # PUT
            # プットの場合は株を購入
            self._handle_stock_purchase(
                contract.underlying,
                pos.quantity * Decimal('100'),
                contract.strike,
                Decimal('0')
            )

        # オプションポジション削除
        del self._option_positions[contract.full_symbol]
        logging.info(f"オプション割当を記録: {contract.full_symbol}, 損失: {realized_gain}")