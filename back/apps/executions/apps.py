from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ExecutionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.executions"
    verbose_name = _('执行管理')
