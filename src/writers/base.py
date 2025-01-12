# src/writers/base.py
from abc import ABC, abstractmethod
from typing import List
from ..models.data_models import DividendRecord

class ReportWriter(ABC):
    @abstractmethod
    def write(self, records: List[DividendRecord]) -> None:
        pass

