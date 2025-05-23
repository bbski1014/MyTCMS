from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    verbose_name = _('项目管理')
