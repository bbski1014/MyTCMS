from __future__ import absolute_import, unicode_literals

# 确保 celery app 在 Django 启动时被加载，这样 @shared_task 装饰器才能找到它
from .celery import app as celery_app

__all__ = ('celery_app',)
