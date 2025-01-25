from typing import Set

class DividendProcessingConfig:
    """配当処理の設定と定数"""
    
    # 有効な配当アクション
    DIVIDEND_ACTIONS: Set[str] = {
        'DIVIDEND', 
        'CASH DIVIDEND',
        'REINVEST DIVIDEND',
        'REINVEST SHARES',
        'NRA TAX ADJ',
        'PR YR CASH DIV'
    }
    
    # 配当の種類
    DIVIDEND_TYPES = {
        'CASH': 'Cash Dividend',
        'REINVEST': 'Reinvested Dividend',
        'QUALIFIED': 'Qualified Dividend',
        'NON_QUALIFIED': 'Non-Qualified Dividend'
    }
    
    # 配当課税レート
    TAX_RATES = {
        'QUALIFIED': 0.15,   # 優良配当の標準的な税率
        'NON_QUALIFIED': 0.22  # 通常配当の税率
    }