from typing import List, Any
import logging

from .base import BaseWriter

class ConsoleWriter(BaseWriter):
    """コンソール出力クラス"""
    
    def __init__(self):
        # コンソール出力のため、出力パスは不要
        super().__init__()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def write(self, records: List[Any]) -> None:
        """レコードをコンソールに出力"""
        if not records:
            self._logger.warning("No records to display")
            return
        
        try:
            # デモンストレーション用の簡易出力
            print("\n=== Records Summary ===")
            record_type = type(records[0]).__name__
            print(f"Record Type: {record_type}")
            print(f"Total Records: {len(records)}")
            
            # 最初の5レコードの詳細を表示
            for i, record in enumerate(records[:5], 1):
                print(f"\nRecord {i}:")
                print(self._format_record(record))
        
        except Exception as e:
            self._logger.error(f"Error writing to console: {e}")

    def _format_record(self, record: Any) -> str:
        """レコードを文字列にフォーマット"""
        try:
            # レコードの種類に応じて異なる処理
            if hasattr(record, '__dict__'):
                # 辞書形式の属性を文字列化
                record_dict = vars(record)
                return "\n".join(f"{k}: {v}" for k, v in record_dict.items())
            
            # 辞書形式でない場合は文字列に変換
            return str(record)
        
        except Exception as e:
            return f"Error formatting record: {e}"