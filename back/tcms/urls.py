"""
URL configuration for tcms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API文档配置
schema_view = get_schema_view(
    openapi.Info(
        title="TCMS API",
        default_version='v1',
        description="测试用例管理系统 API 文档",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # 根路径重定向到API文档
    path('', RedirectView.as_view(url='/swagger/', permanent=False), name='index'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API文档
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API v1版本路由（使用v1前缀便于后续版本升级）
    path('api/v1/', include([
        # 身份验证
        path('auth/', include('apps.users.auth_urls')),
        # 用户管理
        path('', include('apps.users.urls')),
        # 项目管理
        path('projects/', include('apps.projects.urls')),
        # 测试管理
        path('testcases/', include('apps.testcases.urls')),
        # 文件管理
        path('files/', include('apps.files.urls')),
        # 执行管理
        path('executions/', include('apps.executions.urls')),
    ])),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
