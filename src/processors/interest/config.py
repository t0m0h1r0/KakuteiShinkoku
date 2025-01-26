from typing import Set, Dict
from decimal import Decimal

class InterestProcessingConfig:
    """利子処理の設定と定数"""
    
    # 有効な利子アクション
    INTEREST_ACTIONS: Set[str] = {
        'CREDIT INTEREST',
        'BANK INTEREST', 
        'BOND INTEREST', 
        'CD INTEREST', 
        'CD INTEREST TOTAL',
        'CREDIT', 
        'PR YR BANK INT'
    }
    
    # 利子の種類を判定するマッピング
    INTEREST_TYPES: Dict[str, str] = {
        'CD': 'Certificate of Deposit Interest',
        'BANK': 'Bank Account Interest', 
        'BOND': 'Bond Interest',
        'CREDIT': 'Credit Account Interest',
        'TOTAL': 'Total Interest Income'
    }
    
    # 最小課税対象利子額
    MINIMUM_TAXABLE_INTEREST: Decimal = Decimal('0.01')