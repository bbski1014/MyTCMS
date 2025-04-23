from django.apps import AppConfig


class AnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analysis'

    # 在 ready 方法中导入信号
    def ready(self):
        import apps.analysis.signals # noqa F401

    # 如果使用信号，在这里导入
    # def ready(self):
    #     import apps.analysis.signals 