from pathlib import Path
from .rate_loader import RateLoader
from .rate_validator import RateValidator
from .rate_provider import RateProvider
from .rate_cache import RateCache

def create_rate_provider(rate_file_path: Path, use_cache: bool = True) -> RateProvider:
    """為替レートプロバイダーを作成"""
    loader = RateLoader()
    validator = RateValidator()
    provider = RateProvider(rate_file_path, loader, validator)
    
    if use_cache:
        return RateCache(provider)
    return provider