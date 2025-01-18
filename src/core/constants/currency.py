class Currency:
    """通貨コードの定数"""
    USD = 'USD'
    JPY = 'JPY'
    EUR = 'EUR'
    GBP = 'GBP'
    
    @classmethod
    def is_valid(cls, currency: str) -> bool:
        """通貨コードが有効かを確認"""
        return currency in [cls.USD, cls.JPY, cls.EUR, cls.GBP]
