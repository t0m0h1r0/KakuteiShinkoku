class CleanupHandler:
    """クリーンアップ処理クラス"""
    
    @staticmethod
    def cleanup_context(context):
        """コンテキストのクリーンアップ"""
        # キャッシュのクリア
        if hasattr(context.exchange_rate_provider, 'clear_cache'):
            context.exchange_rate_provider.clear_cache()
        
        # 結果のクリア
        context.processing_results = None
        
        context.logger.info("Application context cleaned up")