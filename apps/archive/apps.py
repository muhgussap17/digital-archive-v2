from django.apps import AppConfig


class ArchiveConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.archive'
    verbose_name = 'Sistem Arsip Digital'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.archive.signals
