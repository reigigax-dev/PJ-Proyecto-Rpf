from django.apps import AppConfig


class RpfApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rpf_api'

    def ready(self):
        from . import signals