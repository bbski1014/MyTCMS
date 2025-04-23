from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TestcasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.testcases"
    verbose_name = _('测试用例管理')
