import os
from celery import Celery
from django.conf import settings

# 设置 Django settings 模块的环境变量
# 'tcms.settings' 指向 back/tcms/settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tcms.settings')

# 创建 Celery 应用实例
# 'tcms' 是你的 Django 项目名
app = Celery('tcms')

# 使用 Django settings.py 中的配置
# CELERY_ 作为前缀的配置项会被自动加载
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有 Django 应用下的 tasks.py 文件
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 