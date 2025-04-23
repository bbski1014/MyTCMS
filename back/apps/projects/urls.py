from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    ProjectTagViewSet, ProjectViewSet, 
    ProjectMemberViewSet, MilestoneViewSet, 
    EnvironmentViewSet, ProjectDocumentViewSet
)
# Import ModuleViewSet from testcases app
from apps.testcases.views import ModuleViewSet 

# 创建主路由器
router = DefaultRouter()
router.register(r'tags', ProjectTagViewSet)
router.register(r'', ProjectViewSet)

# 创建项目的嵌套路由器
project_router = routers.NestedSimpleRouter(router, r'', lookup='project')
project_router.register(r'members', ProjectMemberViewSet, basename='project-members')
project_router.register(r'milestones', MilestoneViewSet, basename='project-milestones')
project_router.register(r'environments', EnvironmentViewSet, basename='project-environments')
project_router.register(r'documents', ProjectDocumentViewSet, basename='project-documents')
# Register modules as a nested resource under projects
project_router.register(r'modules', ModuleViewSet, basename='project-modules') 

# API URL配置
urlpatterns = [
    path('', include(router.urls)),
    path('', include(project_router.urls)),
] 