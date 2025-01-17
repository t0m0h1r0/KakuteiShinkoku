from datetime import date, datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

def parse_date(date_str: str, formats: Tuple[str, ...] = ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y')) -> Optional[date]:
    """
    複数のフォーマットに対応した日付パース
    
    Args:
        date_str: パース対象の日付文字列
        formats: 対応する日付フォーマットのタプル
    
    Returns:
        パースされた日付、失敗時はNone
    """
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    logger.warning(f"Failed to parse date string: {date_str}")
    return None

def calculate_holding_period(purchase_date: date, sale_date: date) -> int:
    """
    保有期間を計算
    
    Args:
        purchase_date: 購入日
        sale_date: 売却日
    
    Returns:
        保有日数
    """
    return (sale_date - purchase_date).days

def is_same_trading_day(date1: date, date2: date) -> bool:
    """
    同一取引日かどうかを判定
    
    Args:
        date1: 比較対象日付1
        date2: 比較対象日付2
    
    Returns:
        同一取引日の場合True
    """
    return date1 == date2

def get_fiscal_year(target_date: date) -> int:
    """
    会計年度を取得
    
    Args:
        target_date: 対象日付
    
    Returns:
        会計年度
    """
    if target_date.month > 3:
        return target_date.year
    return target_date.year - 1

def get_fiscal_period(target_date: date) -> Tuple[date, date]:
    """
    会計期間を取得
    
    Args:
        target_date: 対象日付
    
    Returns:
        (期首日, 期末日)のタプル
    """
    fiscal_year = get_fiscal_year(target_date)
    start_date = date(fiscal_year, 4, 1)
    end_date = date(fiscal_year + 1, 3, 31)
    return start_date, end_date
