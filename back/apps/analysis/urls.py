from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PotentialDuplicatePairViewSet

# 创建一个路由器并注册我们的 ViewSet
router = DefaultRouter()
router.register(r'potential-duplicates', PotentialDuplicatePairViewSet, basename='potential-duplicate-pair')

# API URL 由路由器自动确定。
urlpatterns = [
    path('', include(router.urls)),
] 