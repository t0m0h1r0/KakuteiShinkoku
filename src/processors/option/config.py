from decimal import Decimal
from typing import Set

class OptionProcessingConfig:
    """オプション処理の設定と定数"""
    
    # 1契約あたりの株数
    SHARES_PER_CONTRACT = 100
    
    # 有効なオプションアクション
    OPTION_ACTIONS: Set[str] = {
        'BUY_TO_OPEN', 
        'SELL_TO_OPEN',
        'BUY_TO_CLOSE', 
        'SELL_TO_CLOSE',
        'EXPIRED', 
        'ASSIGNED'
    }
    
    # オプションシンボルのパターン
    OPTION_SYMBOL_PATTERN = r'\d{2}/\d{2}/\d{4}\s+\d+\.\d+\s+[CP]'
    
    # アクション種別
    ACTION_TYPES = {
        'OPEN': {'BUY_TO_OPEN', 'SELL_TO_OPEN'},
        'CLOSE': {'BUY_TO_CLOSE', 'SELL_TO_CLOSE'},
        'EXPIRE': {'EXPIRED'},
        'ASSIGN': {'ASSIGNED'}
    }
    
    # ポジションタイプ
    POSITION_TYPES = {
        'LONG': 'Long',
        'SHORT': 'Short'
    }