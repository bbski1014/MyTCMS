from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Project, ProjectTag, ProjectMember, Milestone, Environment, ProjectDocument
# Import gettext_lazy for labels
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'code']
        ref_name = 'EnvironmentProjectSimple' # Use a specific ref_name

class UserSerializer(serializers.ModelSerializer):
    """用户简略信息序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'name', 'email', 'role']
        ref_name = 'ProjectUser'


class ProjectTagSerializer(serializers.ModelSerializer):
    """项目标签序列化器"""
    class Meta:
        model = ProjectTag
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    """项目基本信息序列化器"""
    tags = ProjectTagSerializer(many=True, read_only=True)
    creator = UserSerializer(read_only=True)
    manager = UserSerializer(read_only=True)
    
    # 统计信息
    member_count = serializers.SerializerMethodField()
    milestone_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'code', 'description', 'status', 'priority', 
            'start_date', 'end_date', 'creator', 'manager', 'tags', 
            'created_at', 'updated_at', 'test_case_count', 'bug_count',
            'member_count', 'milestone_count'
        ]
    
    def get_member_count(self, obj):
        return obj.members.filter(is_active=True).count()
    
    def get_milestone_count(self, obj):
        return obj.milestones.count()


class ProjectCreateSerializer(serializers.ModelSerializer):
    """项目创建序列化器"""
    class Meta:
        model = Project
        fields = ['name', 'code', 'description', 'status', 'priority', 
                 'start_date', 'end_date', 'manager', 'tags']
    
    def create(self, validated_data):
        # 获取标签，如果有的话
        tags = validated_data.pop('tags', [])
        # 创建项目
        project = Project.objects.create(**validated_data)
        # 添加标签
        if tags:
            project.tags.set(tags)
        
        # 自动将创建者添加为项目成员(项目经理)
        creator = self.context['request'].user
        ProjectMember.objects.create(
            project=project,
            user=creator,
            role='project_manager',
            can_manage_members=True,
            can_manage_test_cases=True,
            can_manage_executions=True
        )
        
        return project


class ProjectDetailSerializer(ProjectSerializer):
    """项目详细信息序列化器"""
    # 添加标签ID列表用于编辑
    tag_ids = serializers.PrimaryKeyRelatedField(
        source='tags',
        queryset=ProjectTag.objects.all(),
        many=True,
        required=False
    )
    
    class Meta:
        model = Project
        fields = ProjectSerializer.Meta.fields + ['tag_ids']


class ProjectMemberSerializer(serializers.ModelSerializer):
    """项目成员序列化器"""
    user = UserSerializer(read_only=True)
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = ProjectMember
        fields = '__all__'


class ProjectMemberCreateSerializer(serializers.ModelSerializer):
    """项目成员创建序列化器"""
    user_id = serializers.PrimaryKeyRelatedField(
        source='user',
        queryset=User.objects.all()
    )
    
    class Meta:
        model = ProjectMember
        fields = ['user_id', 'role', 'can_manage_members', 'can_manage_test_cases', 'can_manage_executions']
    
    def validate(self, data):
        # 检查用户是否已经是项目成员
        project = self.context['project']
        user = data.get('user')
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError("该用户已经是项目成员")
        return data


class MilestoneSerializer(serializers.ModelSerializer):
    """里程碑序列化器"""
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Milestone
        fields = '__all__'
        

class EnvironmentSerializer(serializers.ModelSerializer):
    """测试环境序列化器 (改进版)"""
    project_info = ProjectSimpleSerializer(source='project', read_only=True)
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(), 
        write_only=True, 
        label=_('所属项目')
    ) 
    
    class Meta:
        model = Environment
        fields = [
            'id', 
            'name', 
            'description', 
            'project',        # Write-only field
            'project_info',   # Read-only field
            'server_url', 
            'api_base_url', 
            'database_config', 
            'env_variables', 
            'is_active', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['project_info', 'created_at', 'updated_at']


class ProjectDocumentSerializer(serializers.ModelSerializer):
    """项目文档序列化器"""
    project = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by = UserSerializer(read_only=True)
    
    class Meta:
        model = ProjectDocument
        fields = '__all__'
        
    def create(self, validated_data):
        # 设置创建者
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectBriefSerializer(serializers.ModelSerializer):
    """项目摘要信息序列化器，用于列表显示"""
    tags = ProjectTagSerializer(many=True, read_only=True)
    manager_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'code', 'status', 'priority', 'manager_name', 
                  'start_date', 'end_date', 'tags', 'test_case_count', 'bug_count', 'created_at']
    
    def get_manager_name(self, obj):
        return obj.manager.name if obj.manager else None 