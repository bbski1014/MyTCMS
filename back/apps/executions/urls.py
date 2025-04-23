from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TestPlanViewSet, TestRunViewSet, TestResultViewSet

router = DefaultRouter()
router.register(r'testplans', TestPlanViewSet, basename='testplan')
router.register(r'testruns', TestRunViewSet, basename='testrun')
router.register(r'testresults', TestResultViewSet, basename='testresult')
# 以后可以添加 TestRunViewSet 等

urlpatterns = [
    path('', include(router.urls)),
    # 未来可以添加其他非 ViewSet 的 URL
] 