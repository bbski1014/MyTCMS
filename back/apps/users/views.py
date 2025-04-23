# apps/users/views.py
from django.contrib.auth import get_user_model, authenticate, login, logout
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from django.db.models import Avg, Count, F, Q, Sum
from django.shortcuts import get_object_or_404
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models.functions import TruncDate
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend

from .models import Skill, UserSkill, Device, UserRating, UserReward, DeviceType, SkillType, ExchangeRecord
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, CustomTokenObtainPairSerializer,
    SkillSerializer, UserSkillSerializer, DeviceSerializer,
    UserRatingSerializer, UserRewardSerializer, UserProfileSerializer,
    DeviceTypeSerializer, SkillTypeSerializer,
    UserRewardCreateSerializer, ExchangeRecordSerializer,
    UserRatingOverviewSerializer
)
from .permissions import IsOwnerOrReadOnly # Use local import

User = get_user_model()

class CustomTokenObtainPairView(TokenObtainPairView):
    """自定义Token获取视图"""
    serializer_class = CustomTokenObtainPairSerializer

class TokenAuthView(ObtainAuthToken):
    """DRF Token认证视图"""
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email,
            'name': getattr(user, 'name', ''),
            'role': getattr(user, 'role', ''),
        })

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """兼容前端的普通登录视图"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    # 如果使用表单数据格式
    if not username and 'username' in request.POST:
        username = request.POST.get('username')
        password = request.POST.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user:
        login(request, user)
        
        # 包含用户资料
        user_serializer = UserSerializer(user)
        
        return Response({
            'success': True,
            'message': '登录成功',
            'user': user_serializer.data
        })
    
    return Response({
        "success": False,
        "error": "用户名或密码不正确"
    }, status=400)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_view(request):
    """用户注册视图"""
    serializer = UserCreateSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        
        # 自动登录
        login(request, user)
        
        # 包含用户资料
        user_serializer = UserSerializer(user)
        
        return Response({
            'success': True,
            'message': '注册成功',
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """用户登出视图"""
    logout(request)
    return Response({
        'success': True,
        'message': '已成功登出'
    })

class UserViewSet(viewsets.ModelViewSet):
    """用户视图集"""
    queryset = User.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'name', 'email', 'phone', 'department', 'role']
    ordering_fields = ['username', 'date_joined', 'name', 'role']
    ordering = ['-date_joined']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        if self.action in [
                'me', 'change_password', 
                'my_skills', 'my_devices', 
                'my_ratings', 'my_rewards', 
                'total_points',
                'exchange_history', 
                'ratings_overview',
                'user_stats'
            ]:
            return [permissions.IsAuthenticated()]
        # admin权限或具有相应权限
        return [permissions.IsAdminUser()]
    
    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """获取/更新当前用户信息"""
        user = request.user
        
        if request.method == 'GET':
            serializer = UserSerializer(user)
            return Response(serializer.data)
        
        elif request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = UserUpdateSerializer(user, data=request.data, partial=partial)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """修改密码"""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"success": True, "message": "密码修改成功"}, status=status.HTTP_200_OK)
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='stats')
    def user_stats(self, request):
        """获取用户统计数据，例如今日新增用户。"""
        from django.utils import timezone
        today = timezone.now().date()
        
        new_today_count = User.objects.filter(date_joined__date=today).count()
        
        # 可以扩展添加更多统计数据
        total_count = self.get_queryset().count() # Use viewset's queryset for total
        
        return Response({
            'total_users': total_count,
            'new_today_count': new_today_count,
            # 'active_last_week': ... # Example for future extension
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_skills(self, request):
        """获取当前用户的技能"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        skills = UserSkill.objects.filter(user=request.user)
        serializer = UserSkillSerializer(skills, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_devices(self, request):
        """获取当前用户的设备"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        devices = Device.objects.filter(user=request.user)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_ratings(self, request):
        """获取当前用户的评分"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        ratings = UserRating.objects.filter(user=request.user)
        serializer = UserRatingSerializer(ratings, many=True)
        
        # 计算平均评分
        avg_rating = ratings.aggregate(
            avg_score=Avg('score'),
            avg_quality=Avg('quality_score'),
            avg_efficiency=Avg('efficiency_score'),
            avg_communication=Avg('communication_score')
        )
        
        return Response({
            'ratings': serializer.data,
            'statistics': avg_rating
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_rewards(self, request):
        """获取当前用户的奖励"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        rewards = UserReward.objects.filter(user=request.user)
        serializer = UserRewardSerializer(rewards, many=True)
        
        # 计算总奖励
        total_points = sum(reward.amount for reward in rewards if reward.reward_type == 'point')
        
        return Response({
            'rewards': serializer.data,
            'total_points': total_points
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def total_points(self, request):
        """获取当前用户的总积分"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Calculate total points from UserReward model
        total_points = UserReward.objects.filter(user=request.user, reward_type='point').aggregate(total=Sum('amount'))['total'] or 0
        
        # Alternatively, if points are stored directly on UserProfile:
        # total_points = request.user.profile.points if hasattr(request.user, 'profile') else 0
        
        return Response({'total_points': total_points})

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def exchange_history(self, request):
        """获取当前用户的积分兑换历史"""
        if not request.user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
            
        exchange_records = ExchangeRecord.objects.filter(user=request.user)
        
        # Apply pagination
        page = self.paginate_queryset(exchange_records)
        if page is not None:
            serializer = ExchangeRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = ExchangeRecordSerializer(exchange_records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def ratings_overview(self, request):
        """获取用户评级概览数据 (列表和分布)"""
        # Get all active users (or apply other relevant filters)
        # Use select_related('profile') to optimize fetching profile data
        users = User.objects.filter(is_active=True).select_related('profile') 
        
        # --- Data for the List/Table --- 
        # Paginate the user list
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = UserRatingOverviewSerializer(page, many=True)
            paginated_user_data = self.get_paginated_response(serializer.data).data
        else:
             # Should not happen if pagination is configured, but handle anyway
            serializer = UserRatingOverviewSerializer(users, many=True)
            # Manually structure pagination-like response if needed
            paginated_user_data = {
                'count': users.count(),
                'next': None,
                'previous': None,
                'results': serializer.data
            }
            
        # --- Data for the Distribution Chart --- 
        # Calculate distribution based on UserProfile.level or a calculated level
        # This is a simplified example assuming level maps somewhat to S/A/B/C/D
        # You might need a more complex mapping function based on score or profile level
        level_distribution = {
            'S': users.filter(profile__level__gte=5).count(), # Example mapping: level 5+ = S
            'A': users.filter(profile__level=4).count(),      # Example mapping: level 4 = A
            'B': users.filter(profile__level=3).count(),      # Example mapping: level 3 = B
            'C': users.filter(profile__level=2).count(),      # Example mapping: level 2 = C
            'D': users.filter(profile__level__lte=1).count() # Example mapping: level 1 = D
        }
        
        # Combine results
        response_data = { 
            'users': paginated_user_data, # Contains count, next, previous, results
            'distribution': level_distribution
        }
        
        return Response(response_data)


class SkillViewSet(viewsets.ModelViewSet):
    """技能视图集"""
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class UserSkillViewSet(viewsets.ModelViewSet):
    """用户技能视图集"""
    serializer_class = UserSkillSerializer
    permission_classes = [permissions.IsAuthenticated]  # 添加默认权限类
    filter_backends = [filters.SearchFilter]
    search_fields = ['skill__name', 'skill__category']
    
    def get_queryset(self):
        """根据当前用户筛选技能"""
        # 确保用户已认证
        if not self.request.user.is_authenticated:
            return UserSkill.objects.none()  # 返回空查询集
            
        user_id = self.kwargs.get('user_pk')
        if user_id:
            return UserSkill.objects.filter(user_id=user_id)
        return UserSkill.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """创建时关联到当前用户"""
        user_id = self.kwargs.get('user_pk')
        if user_id and self.request.user.is_staff:
            # 管理员可以为其他用户添加技能
            serializer.save(user_id=user_id)
        else:
            # 普通用户只能为自己添加技能
            serializer.save(user=self.request.user)
    
    def get_permissions(self):
        if self.request.user.is_staff:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


class DeviceViewSet(viewsets.ModelViewSet):
    """设备视图集"""
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]  # 添加默认权限类
    
    def get_queryset(self):
        """根据当前用户筛选设备"""
        # 确保用户已认证
        if not self.request.user.is_authenticated:
            return Device.objects.none()  # 返回空查询集
            
        user_id = self.kwargs.get('user_pk')
        if user_id and self.request.user.is_staff:
            # 使用select_related优化查询
            return Device.objects.filter(user_id=user_id).select_related('device_type')
        return Device.objects.filter(user=self.request.user).select_related('device_type')
    
    def perform_create(self, serializer):
        """创建时关联到当前用户，并处理device_type"""
        user_id = self.kwargs.get('user_pk')
        
        # 处理device_type
        device_type_id = self.request.data.get('device_type')
        device_type_name = self.request.data.get('device_type_name', '')
        
        # 如果是字符串，尝试查找或创建DeviceType
        if isinstance(device_type_id, str) and not device_type_id.isdigit():
            try:
                device_type = DeviceType.objects.get(name__iexact=device_type_id)
                device_type_id = device_type.id
            except DeviceType.DoesNotExist:
                # 如果是预定义类型，创建它
                if device_type_id in dict(Device.DEVICE_TYPE_CHOICES):
                    device_type = DeviceType.objects.create(
                        name=device_type_id,
                        category='系统默认',
                        description=f'{dict(Device.DEVICE_TYPE_CHOICES)[device_type_id]}'
                    )
                    device_type_id = device_type.id
        
        # 关联用户和设备类型
        if user_id and self.request.user.is_staff:
            # 管理员可以为其他用户添加设备
            serializer.save(user_id=user_id, device_type_id=device_type_id)
        else:
            # 普通用户只能为自己添加设备
            serializer.save(user=self.request.user, device_type_id=device_type_id)
    
    def get_permissions(self):
        """获取或更新自己的设备只需要登录权限"""
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


# 兼容前端API的设备视图
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def user_devices(request):
    """
    GET: 获取当前用户的设备列表
    POST: 添加用户设备
    """
    if not request.user.is_authenticated:
        return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
    if request.method == 'GET':
        devices = Device.objects.filter(user=request.user).select_related('device_type')
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # 处理device_type_name字段，查找或创建对应的DeviceType对象
        device_type_name = request.data.get('device_type_name')
        device_type_id = request.data.get('device_type')
        
        # 如果提供了设备类型名称但没有ID，查找或创建设备类型
        if not device_type_id and device_type_name:
            try:
                device_type = DeviceType.objects.get(name__iexact=device_type_name)
            except DeviceType.DoesNotExist:
                # 创建新的设备类型
                device_type = DeviceType.objects.create(
                    name=device_type_name,
                    category='用户创建',
                    description=f'用户 {request.user.username} 创建的设备类型'
                )
            device_type_id = device_type.id
            
        # 如果提供了设备类型但未提供ID，查找或创建设备类型
        device_type_str = request.data.get('device_type')
        if isinstance(device_type_str, str) and not device_type_id:
            try:
                device_type = DeviceType.objects.get(name__iexact=device_type_str)
                device_type_id = device_type.id
            except DeviceType.DoesNotExist:
                # 如果是预定义的类型，则创建
                if device_type_str in dict(Device.DEVICE_TYPE_CHOICES):
                    device_type = DeviceType.objects.create(
                        name=device_type_str,
                        category='系统默认',
                        description=f'{dict(Device.DEVICE_TYPE_CHOICES)[device_type_str]}'
                    )
                    device_type_id = device_type.id
                else:
                    return Response({"error": "请选择有效的设备类型"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 确保有device_type_id
        if not device_type_id:
            return Response({"error": "请选择设备类型"}, status=status.HTTP_400_BAD_REQUEST)
            
        # 准备数据
        data = request.data.copy()
        data['device_type'] = device_type_id
        
        serializer = DeviceSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def user_device_detail(request, device_id):
    """
    GET: 获取单个设备详情
    PUT: 更新用户设备
    DELETE: 删除用户设备
    """
    if not request.user.is_authenticated:
        return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        device = Device.objects.get(id=device_id, user=request.user)
    except Device.DoesNotExist:
        return Response({"error": "设备不存在或您无权访问"}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        serializer = DeviceSerializer(device)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = DeviceSerializer(device, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 兼容前端API的用户技能视图
@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def user_skills(request):
    """
    GET: 获取当前用户的技能列表
    POST: 添加用户技能
    """
    if not request.user.is_authenticated:
        return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
    if request.method == 'GET':
        skills = UserSkill.objects.filter(user=request.user).select_related('skill', 'skill__skill_type')
        serializer = UserSkillSerializer(skills, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        # 通过ID或名称添加技能
        skill_id = request.data.get('skill')
        skill_name = request.data.get('skill_name', '').strip()
        skill_type_id = request.data.get('skill_type_id')  # 新增：技能类型ID
        
        print(f"添加技能请求: skill_id={skill_id}, skill_name={skill_name}, skill_type_id={skill_type_id}")
        
        # 如果提供了技能名称但没有ID，尝试查找或创建技能
        if not skill_id and skill_name:
            # 查找是否已存在该技能
            try:
                skill = Skill.objects.get(name__iexact=skill_name)
                print(f"找到现有技能: {skill.name} (ID: {skill.id})")
            except Skill.DoesNotExist:
                # 如果不存在，则创建新技能
                skill_data = {
                    'name': skill_name,
                    'category': '用户创建',
                    'description': f'用户 {request.user.username} 创建的技能'
                }
                
                # 如果提供了技能类型ID，添加到技能中
                if skill_type_id:
                    try:
                        skill_type = SkillType.objects.get(id=skill_type_id)
                        skill_data['skill_type'] = skill_type
                    except SkillType.DoesNotExist:
                        pass
                
                skill = Skill.objects.create(**skill_data)
                print(f"创建新技能: {skill.name} (ID: {skill.id})")
            skill_id = skill.id
        
        # 如果仍然没有技能ID，返回错误
        if not skill_id:
            return Response({"error": "请选择技能或提供技能名称"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            skill = Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            return Response({"error": "所选技能不存在"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 检查用户是否已有该技能
        if UserSkill.objects.filter(user=request.user, skill=skill).exists():
            return Response({"error": "您已添加过该技能"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 准备数据并创建用户技能
        skill_data = {
            'skill': skill.id,
            'proficiency': 1,  # 默认熟练度
            'years_experience': request.data.get('years_experience', 0)
        }
        
        # 如果提供了level，转换为proficiency
        level = request.data.get('level')
        if level:
            level_mapping = {
                '初级': 1,
                '中级': 2,
                '高级': 3,
                '专家': 4
            }
            skill_data['proficiency'] = level_mapping.get(level, 1)
        
        serializer = UserSkillSerializer(data=skill_data)
        if serializer.is_valid():
            user_skill = serializer.save(user=request.user)
            # 返回带有技能名称的完整信息
            result = serializer.data
            result['name'] = skill.name
            result['level'] = level or '初级'
            
            # 添加技能类型信息
            if skill.skill_type:
                result['skill_type_name'] = skill.skill_type.name
                result['skill_type_id'] = skill.skill_type.id
            
            print(f"成功添加用户技能: {skill.name}")
            return Response(result, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def user_skill_detail(request, skill_id):
    """
    GET: 获取单个用户技能详情
    PUT: 更新用户技能
    DELETE: 删除用户技能
    """
    if not request.user.is_authenticated:
        return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
    user_skill = get_object_or_404(UserSkill, id=skill_id, user=request.user)
    
    if request.method == 'GET':
        serializer = UserSkillSerializer(user_skill)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = UserSkillSerializer(user_skill, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        user_skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def skills_search(request):
    """搜索技能"""
    search_term = request.query_params.get('search', '')
    if search_term:
        skills = Skill.objects.filter(name__icontains=search_term)[:20]
        serializer = SkillSerializer(skills, many=True)
        return Response(serializer.data)
    return Response([])

# 提供明确的密码修改API
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """修改密码视图"""
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"success": True, "message": "密码修改成功"}, status=status.HTTP_200_OK)
    return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# 技能类型视图集
class SkillTypeViewSet(viewsets.ModelViewSet):
    """技能类型管理视图集"""
    queryset = SkillType.objects.all()
    serializer_class = SkillTypeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    # Explicitly define allowed methods for the standard actions
    # ModelViewSet provides list, create, retrieve, update, partial_update, destroy
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options'] 
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

# 设备类型视图集
class DeviceTypeViewSet(viewsets.ModelViewSet):
    """设备类型管理视图集"""
    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'category']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取设备类型统计信息"""
        # 使用外键关系统计设备数量
        device_types = DeviceType.objects.annotate(
            device_count=Count('devices')
        ).values('id', 'name', 'category', 'device_count')
        
        # 没有必要分别获取自定义类型，因为现在所有设备都关联到DeviceType
        
        return Response(list(device_types))

# 添加技能统计数据API
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def skill_statistics(request):
    """获取技能统计数据"""
    # 1. 按技能类型统计用户数量
    skill_distribution = Skill.objects.annotate(
        user_count=Count('userskill')
    ).values('id', 'name', 'category', 'user_count')
    
    # 2. 按技能熟练度等级分布
    skill_levels = {}
    for skill in skill_distribution:
        skill_id = skill['id']
        # 获取该技能的不同熟练度级别的用户数量
        levels = UserSkill.objects.filter(skill_id=skill_id).values('proficiency').annotate(
            count=Count('id')
        )
        
        # 转换为前端期望的格式
        level_dist = {
            'junior': 0,
            'intermediate': 0,
            'senior': 0
        }
        
        total = 0
        for level in levels:
            if level['proficiency'] <= 1:
                level_dist['junior'] += level['count']
            elif level['proficiency'] <= 3:
                level_dist['intermediate'] += level['count']
            else:
                level_dist['senior'] += level['count']
            total += level['count']
        
        # 计算百分比
        if total > 0:
            level_dist['junior'] = round(level_dist['junior'] * 100 / total)
            level_dist['intermediate'] = round(level_dist['intermediate'] * 100 / total)
            level_dist['senior'] = round(level_dist['senior'] * 100 / total)
        
        skill_levels[skill_id] = level_dist
    
    # 3. 合并数据
    result = []
    for skill in skill_distribution:
        skill_id = skill['id']
        total_users = User.objects.count()
        percentage = 0
        if total_users > 0:
            percentage = round(skill['user_count'] * 100 / total_users)
        
        result.append({
            'skillType': skill['name'],
            'count': skill['user_count'],
            'percentage': percentage,
            'levelDistribution': skill_levels.get(skill_id, {'junior': 0, 'intermediate': 0, 'senior': 0})
        })
    
    return Response(result)

# 添加设备统计数据API
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def device_statistics(request):
    """获取设备统计数据"""
    # 1. 按设备类型统计
    device_types = Device.objects.values(
        'device_type__name', 'device_type__category'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 2. 按操作系统统计
    os_stats = Device.objects.values('os').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 3. 计算总设备数和百分比
    total_devices = Device.objects.count()
    
    # 格式化设备类型数据
    device_type_data = []
    for dt in device_types:
        percentage = 0
        if total_devices > 0:
            percentage = round(dt['count'] * 100 / total_devices)
        
        # 获取该类型设备的操作系统分布
        os_distribution = Device.objects.filter(
            device_type__name=dt['device_type__name']
        ).values('os').annotate(
            count=Count('id')
        ).order_by('-count')
        
        device_type_data.append({
            'name': dt['device_type__name'],
            'category': dt['device_type__category'],
            'count': dt['count'],
            'percentage': percentage,
            'os_distribution': list(os_distribution)
        })
    
    # 格式化操作系统数据
    os_data = []
    for os in os_stats:
        percentage = 0
        if total_devices > 0:
            percentage = round(os['count'] * 100 / total_devices)
        
        os_data.append({
            'name': os['os'],
            'count': os['count'],
            'percentage': percentage
        })
    
    result = {
        'deviceTypes': device_type_data,
        'osSystems': os_data,
        'totalDevices': total_devices
    }
    
    return Response(result)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unified_skills_search(request):
    """统一搜索技能和技能类型，返回合并结果"""
    search_term = request.query_params.get('search', '')
    type_id = request.query_params.get('type_id')
    
    # 查询技能
    skills_queryset = Skill.objects.filter(
        Q(name__icontains=search_term) | Q(category__icontains=search_term)
    )
    
    # 如果指定了类型ID，则筛选该类型下的技能
    if type_id:
        skills_queryset = skills_queryset.filter(skill_type_id=type_id)
    
    # 查询技能类型
    skill_types_queryset = SkillType.objects.filter(
        Q(name__icontains=search_term) | Q(category__icontains=search_term)
    )
    
    # 序列化结果
    skills_serializer = SkillSerializer(skills_queryset, many=True)
    skill_types_serializer = SkillTypeSerializer(skill_types_queryset, many=True)
    
    # 返回合并结果
    return Response({
        'skills': skills_serializer.data,
        'skill_types': skill_types_serializer.data
    })


# 密码重置相关功能
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """请求密码重置，发送重置链接到用户邮箱"""
    email = request.data.get('email')
    
    if not email:
        return Response({'success': False, 'message': '请提供邮箱地址'}, status=400)
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # 为了安全，不告诉用户邮箱是否存在
        return Response({'success': True, 'message': '如果该邮箱已注册，我们已向其发送了重置链接'})
    
    # 生成重置令牌
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    
    # 构建重置链接
    reset_url = f"{request.scheme}://{request.get_host()}/#/reset-password?uid={uid}&token={token}"
    
    # 发送重置邮件
    try:
        # 构建邮件内容
        subject = "TCMS - 重置密码"
        message = f"""
        您好，

        您收到此邮件是因为有人请求重置您在TCMS系统中的密码。

        请点击以下链接重置密码：
        {reset_url}

        如果您并未请求重置密码，请忽略此邮件。

        祝好,
        TCMS团队
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        return Response({'success': True, 'message': '重置链接已发送到您的邮箱'})
    except Exception as e:
        print(f"发送邮件出错: {e}")
        return Response({'success': False, 'message': '发送邮件失败，请稍后再试'}, status=500)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """确认密码重置，使用新密码更新用户账户"""
    uid = request.data.get('uid')
    token = request.data.get('token')
    new_password = request.data.get('new_password')
    
    if not uid or not token or not new_password:
        return Response({'success': False, 'message': '缺少必要参数'}, status=400)
    
    try:
        # 解码uid获取用户ID
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({'success': False, 'message': '无效的用户'}, status=400)
    
    # 验证token
    if not default_token_generator.check_token(user, token):
        return Response({'success': False, 'message': '无效或已过期的重置链接'}, status=400)
    
    # 更新密码
    user.set_password(new_password)
    user.save()
    
    return Response({'success': True, 'message': '密码已成功重置，请使用新密码登录'})

class UserRatingViewSet(viewsets.ModelViewSet):
    """用户评分视图集"""
    queryset = UserRating.objects.all()
    serializer_class = UserRatingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # Base permission
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'rated_by', 'project_id', 'task_id']
    ordering_fields = ['created_at', 'score']
    ordering = ['-created_at']

    def get_permissions(self):
        """创建需要登录，修改/删除需要是评分人或管理员"""
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Need a permission like IsOwnerOrAdmin (checking request.user == obj.rated_by)
            # Using IsAdminUser for now, can refine later - Replace with IsOwnerOrReadOnly
            # return [permissions.IsAdminUser()]
            return [IsOwnerOrReadOnly()] # Apply the owner check permission
        # Fallback to default IsAuthenticatedOrReadOnly for list/retrieve
        return super().get_permissions()

    def perform_create(self, serializer):
        """创建评分时自动设置评分人"""
        serializer.save(rated_by=self.request.user)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_given(self, request):
        """获取当前用户给出的评分"""
        given_ratings = UserRating.objects.filter(rated_by=request.user)
        page = self.paginate_queryset(given_ratings)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(given_ratings, many=True)
        return Response(serializer.data)

# --- Add Custom Permission Class ---
class IsAdminOrManager(permissions.BasePermission):
    """
    Custom permission to allow access only to admin users or managers.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated first
        if not request.user or not request.user.is_authenticated:
            return False
        # Allow if user is admin (staff) or their role is 'manager'
        return request.user.is_staff or getattr(request.user, 'role', None) == 'manager'

class UserRewardViewSet(viewsets.ModelViewSet):
    """用户奖励视图集"""
    queryset = UserReward.objects.all()
    serializer_class = UserRewardSerializer
    # permission_classes = [permissions.IsAdminUser] # Remove base permission
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'issued_by', 'reward_type', 'issuance_type', 'project_id', 'task_id']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    # We might need a UserRewardCreateSerializer later - Now we have it
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRewardCreateSerializer
        return UserRewardSerializer # Use standard for other actions

    def get_permissions(self):
        """
        管理员可以执行所有操作。
        项目经理可以创建奖励。
        """
        if self.action == 'create':
            # Allow Admin or Manager to create rewards
            return [IsAdminOrManager()]
        # For list, retrieve, update, partial_update, destroy, only allow Admin
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        """手动创建奖励时设置发放人和类型"""
        # Ensure points are positive or handle appropriately
        amount = serializer.validated_data.get('amount', 0)
        if amount <= 0:
             raise serializers.ValidationError("奖励积分必须为正数。") # Or handle as needed

        instance = serializer.save(issued_by=self.request.user, issuance_type='manual')
        
        # Update user's total points in UserProfile if applicable
        try:
            user_profile = instance.user.profile
            if instance.reward_type == 'point':
                user_profile.points = (user_profile.points or 0) + instance.amount
                user_profile.save(update_fields=['points'])
        except User.profile.RelatedObjectDoesNotExist:
            # Handle case where user profile might not exist yet
            print(f"Warning: UserProfile not found for user {instance.user.id} when issuing reward.")
        except AttributeError:
             # Handle case where user object might not have profile attribute
             print(f"Warning: User {instance.user.id} does not have a profile attribute.")

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated]) # Or AllowAny if needed
def get_reward_type_choices(request):
    """获取用户奖励模型中定义的奖励类型选项"""
    choices = UserReward.REWARD_TYPE_CHOICES
    formatted_choices = [{'value': choice[0], 'label': choice[1]} for choice in choices]
    return Response(formatted_choices)