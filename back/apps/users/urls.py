from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import (
    UserViewSet, SkillViewSet, UserSkillViewSet, DeviceViewSet, 
    user_devices, user_device_detail, user_skills, user_skill_detail, skills_search,
    TokenAuthView, change_password_view, SkillTypeViewSet, DeviceTypeViewSet,
    skill_statistics, device_statistics, unified_skills_search,
    UserRatingViewSet,
    UserRewardViewSet,
    get_reward_type_choices
)

# 主路由器
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'skills', SkillViewSet)
router.register(r'skill-types', SkillTypeViewSet, basename='skilltype')
router.register(r'devices/types', DeviceTypeViewSet, basename='device-types')
router.register(r'ratings', UserRatingViewSet)
router.register(r'rewards', UserRewardViewSet)

# 嵌套路由器，用于用户相关资源
user_router = routers.NestedSimpleRouter(router, r'users', lookup='user')
user_router.register(r'skills', UserSkillViewSet, basename='user-skills')
user_router.register(r'devices', DeviceViewSet, basename='user-devices')

urlpatterns = [
    # 当前用户的特殊路径 - 放在最前面优先匹配
    path('users/me/skills/', user_skills, name='current-user-skills'),
    path('users/me/skills/<int:skill_id>/', user_skill_detail, name='current-user-skill-detail'),
    path('users/me/devices/', user_devices, name='current-user-devices'),
    path('users/me/devices/<int:device_id>/', user_device_detail, name='current-user-device-detail'),
    path('users/me/change-password/', change_password_view, name='change-password'),
    path('users/me/rewards/', UserViewSet.as_view({'get': 'my_rewards'}), name='current-user-rewards'),
    path('users/me/total_points/', UserViewSet.as_view({'get': 'total_points'}), name='current-user-total-points'),
    path('users/rewards/exchange/history/', UserViewSet.as_view({'get': 'exchange_history'}), name='current-user-exchange-history'),
    
    # 统计数据API
    path('skills/statistics/', skill_statistics, name='skill-statistics'),
    path('devices/statistics/', device_statistics, name='device-statistics'),
    
    # 技能搜索API
    path('skills/search/', skills_search, name='skills-search'),
    
    # 统一技能搜索API
    path('skills/unified-search/', unified_skills_search, name='unified-skills-search'),
    
    # 兼容旧版认证API
    path('token-auth/', TokenAuthView.as_view(), name='token_auth'),
    
    # Rewards specific endpoints
    path('rewards/types/', get_reward_type_choices, name='reward-type-choices'),
    
    # DRF 路由 - 放在后面
    path('', include(router.urls)),
    path('', include(user_router.urls)),
] 