from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import login_view, register_view, logout_view, CustomTokenObtainPairView, password_reset_request, password_reset_confirm

urlpatterns = [
    # 基本认证
    path('login/', login_view, name='api-login'),
    path('register/', register_view, name='api-register'),
    path('logout/', logout_view, name='api-logout'),
    
    # 密码重置
    path('password-reset-request/', password_reset_request, name='password-reset-request'),
    path('password-reset-confirm/', password_reset_confirm, name='password-reset-confirm'),
    
    # JWT认证
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
] 