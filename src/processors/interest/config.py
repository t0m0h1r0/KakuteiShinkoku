from typing import Set
from decimal import Decimal

class InterestProcessingConfig:
    """利子処理の設定と定数"""
    
    # 有効な利子アクション
    INTEREST_ACTIONS: Set[str] = {
        'CREDIT INTEREST',
        'BANK INTEREST',
        'BOND INTEREST',
        'CD INTEREST',
        'PR YR BANK INT'
    }
    
    # 利子の種類
    INTEREST_TYPES = {
        'CD': 'Certificate of Deposit Interest',
        'BANK': 'Bank Account Interest',
        'BOND': 'Bond Interest',
        'CREDIT': 'Credit Account Interest'
    }
    
    # 利子の課税レート
    TAX_RATES = {
        'BANK': 0.22,   # 通常の利子所得税率
        'BOND': 0.20,   # 債券利子の税率
        'CD': 0.22      # 預金証書の利子税率
    }
    
    # 最小課税対象利子額
    MINIMUM_TAXABLE_INTEREST = Decimal('10.00')