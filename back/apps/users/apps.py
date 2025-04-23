from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    verbose_name = _('用户管理')

    def ready(self):
        """在Django启动时执行的代码"""
        # 导入信号处理器，使用相对导入
        from . import signals
