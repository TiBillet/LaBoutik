from django.apps import AppConfig

class ApicashlessConfig(AppConfig):
    name = 'APIcashless'

    def ready(self):
        import APIcashless.signals

