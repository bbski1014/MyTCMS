# apps/users/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile, Skill, UserSkill, Device, UserRating, UserReward, DeviceType, SkillType, ExchangeRecord

User = get_user_model()

class SkillSerializer(serializers.ModelSerializer):
    """技能序列化器"""
    count = serializers.SerializerMethodField()
    skill_type_name = serializers.ReadOnlyField(source='skill_type.name')
    skill_type_category = serializers.ReadOnlyField(source='skill_type.category')
    
    class Meta:
        model = Skill
        fields = ['id', 'name', 'category', 'description', 'count', 
                 'skill_type', 'skill_type_name', 'skill_type_category']
    
    def get_count(self, obj):
        """获取使用该技能的用户数量"""
        if hasattr(obj, 'user_count'):
            return obj.user_count
        return obj.userskill_set.count()

class SkillTypeSerializer(serializers.ModelSerializer):
    """技能类型序列化器"""
    skill_count = serializers.SerializerMethodField()

    class Meta:
        model = SkillType
        fields = ('id', 'name', 'category', 'description', 'icon', 'order', 'skill_count')
        read_only_fields = ('id', 'skill_count')
    
    def get_skill_count(self, obj):
        """获取该类型下的技能数量"""
        if hasattr(obj, 'skill_count'):
            return obj.skill_count
        return obj.skills.count()

class UserSkillSerializer(serializers.ModelSerializer):
    """用户技能序列化器"""
    skill_name = serializers.ReadOnlyField(source='skill.name')
    skill_category = serializers.ReadOnlyField(source='skill.category')
    skill_type_name = serializers.ReadOnlyField(source='skill.skill_type.name', default=None)
    skill_type_id = serializers.ReadOnlyField(source='skill.skill_type.id', default=None)
    
    class Meta:
        model = UserSkill
        fields = ['id', 'skill', 'skill_name', 'skill_category', 'skill_type_name', 'skill_type_id', 'proficiency', 'years_experience']

class DeviceSerializer(serializers.ModelSerializer):
    """设备序列化器"""
    # 添加设备类型名称用于展示
    device_type_name = serializers.ReadOnlyField(source='device_type.name')
    # 添加设备类型分类用于展示
    device_type_category = serializers.ReadOnlyField(source='device_type.category')
    
    class Meta:
        model = Device
        fields = ['id', 'device_type', 'device_type_name', 'device_type_category', 
                 'name', 'os', 'os_version', 'browser', 
                 'browser_version', 'screen_resolution', 'additional_info']
        read_only_fields = ['device_type_name', 'device_type_category']

class UserRatingSerializer(serializers.ModelSerializer):
    """用户评分序列化器"""
    rated_by_username = serializers.ReadOnlyField(source='rated_by.username')
    
    class Meta:
        model = UserRating
        fields = ['id', 'rated_by', 'rated_by_username', 'project_id', 'task_id', 
                 'score', 'quality_score', 'efficiency_score', 'communication_score', 
                 'comment', 'created_at']

class UserRewardSerializer(serializers.ModelSerializer):
    """用户奖励序列化器"""
    # Fields for displaying related info
    user_username = serializers.ReadOnlyField(source='user.username')
    issued_by_username = serializers.ReadOnlyField(source='issued_by.username', default=None)
    reward_type_display = serializers.ReadOnlyField(source='get_reward_type_display')
    issuance_type_display = serializers.ReadOnlyField(source='get_issuance_type_display')

    class Meta:
        model = UserReward
        fields = ['id', 'user', 'user_username', 'issued_by', 'issued_by_username',
                  'issuance_type', 'issuance_type_display',
                  'reward_type', 'reward_type_display', 'amount', 
                  'description', 'project_id', 'task_id', 'created_at']
        # Make issued_by writable=False in the general serializer if needed
        read_only_fields = ['issued_by'] # Maybe not needed if perform_create handles it

class UserRewardCreateSerializer(serializers.ModelSerializer):
    """用于手动创建用户奖励的序列化器"""
    # user 字段允许通过 ID 指定用户
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = UserReward
        fields = ['user', 'reward_type', 'amount', 'description', 
                  'project_id', 'task_id']
        # issued_by and issuance_type will be set in perform_create

class ExchangeRecordSerializer(serializers.ModelSerializer):
    """积分兑换记录序列化器"""
    user_username = serializers.ReadOnlyField(source='user.username')
    status_display = serializers.ReadOnlyField(source='get_status_display')

    class Meta:
        model = ExchangeRecord
        fields = '__all__' # Include all fields for now

class UserRatingOverviewSerializer(serializers.ModelSerializer):
    """用于用户评级概览的序列化器"""
    # Pull fields from UserProfile
    level = serializers.IntegerField(source='profile.level', read_only=True, default=1)
    score = serializers.FloatField(source='profile.reputation_score', read_only=True, default=0.0)
    completed_tasks = serializers.IntegerField(source='profile.completed_tasks', read_only=True, default=0)
    reward_points = serializers.IntegerField(source='profile.points', read_only=True, default=0)
    # Add other relevant fields from User model directly
    name = serializers.CharField(read_only=True) # Use the name field from User model

    # Placeholder for detailed scores if calculated later
    # skillScore = serializers.FloatField(read_only=True)
    # qualityScore = serializers.FloatField(read_only=True)
    # responseScore = serializers.FloatField(read_only=True)
    # documentScore = serializers.FloatField(read_only=True)

    # Define a method to map numeric level to S/A/B/C/D or use Profile level directly
    # For simplicity, we'll rely on frontend mapping or a direct level field if available

    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'level', 'score', 
                  'completed_tasks', 'reward_points']
        # Add detailed scores here if implemented

class UserProfileSerializer(serializers.ModelSerializer):
    """用户资料序列化器"""
    experience_level_display = serializers.ReadOnlyField(source='get_experience_level_display')
    
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'email_verified', 'identity_verified', 
                 'experience_level', 'experience_level_display', 'points', 'level', 
                 'reputation_score', 'github', 'linkedin', 'website', 
                 'email_notifications', 'completed_tasks', 'bugs_found', 
                 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    profile = UserProfileSerializer(read_only=True)
    skills = UserSkillSerializer(many=True, read_only=True)
    devices = DeviceSerializer(many=True, read_only=True)
    role_display = serializers.ReadOnlyField(source='get_role_display')
    
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'email', 'phone', 'department', 
                  'position', 'role', 'role_display', 'is_active', 'date_joined',
                  'profile', 'skills', 'devices']
        read_only_fields = ['date_joined']

class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    role_display = serializers.ReadOnlyField(source='get_role_display')
    
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'name', 'email', 'phone', 
                  'department', 'position', 'role', 'role_display']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器"""
    profile = UserProfileSerializer(required=False)
    role_display = serializers.ReadOnlyField(source='get_role_display')
    
    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'department', 'position', 'role', 
                 'role_display', 'profile']
    
    def update(self, instance, validated_data):
        # 更新用户资料
        profile_data = validated_data.pop('profile', None)
        if profile_data:
            if hasattr(instance, 'profile'):
                profile = instance.profile
                for attr, value in profile_data.items():
                    setattr(profile, attr, value)
                profile.save()
            else:
                UserProfile.objects.create(user=instance, **profile_data)
        
        # 更新用户信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance

class PasswordChangeSerializer(serializers.Serializer):
    """密码修改序列化器"""
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("旧密码不正确")
        return value

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """自定义Token获取序列化器"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # 添加用户信息到响应
        user = self.user
        data.update({
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
        })
        
        return data

class DeviceTypeSerializer(serializers.ModelSerializer):
    """设备类型序列化器"""
    count = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceType
        fields = ['id', 'name', 'category', 'description', 'count']
    
    def get_count(self, obj):
        """获取使用该设备类型的设备数量"""
        # 直接使用关联的devices反向关系计数
        return obj.devices.count()