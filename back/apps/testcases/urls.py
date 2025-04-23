from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TagViewSet, TestCaseViewSet, TestCaseVersionViewSet

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'versions', TestCaseVersionViewSet, basename='testcase-version')
router.register(r'', TestCaseViewSet, basename='testcase')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
] 