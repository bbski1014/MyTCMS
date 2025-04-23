from rest_framework import serializers
from .models import Module, Tag, TestCase, TestCaseVersion, TestCaseStep
# Import User model if needed for created_by/updated_by representation
from django.contrib.auth import get_user_model 
# Import Project model if needed, adjust path
# from apps.projects.models import Project
from django.utils.translation import gettext_lazy as _
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class TagSerializer(serializers.ModelSerializer):
    """标签序列化器"""
    class Meta:
        model = Tag
        fields = ['id', 'name']

# --- Add TestCaseStepSerializer ---
class TestCaseStepSerializer(serializers.ModelSerializer):
    """序列化器，用于测试用例步骤"""
    class Meta:
        model = TestCaseStep
        fields = ['id', 'version', 'step_number', 'action', 'expected_result']
        # version is usually read-only here as steps are created linked to a version
        read_only_fields = ['id', 'version'] 
        # Make fields required for input, but allow empty for PUT/PATCH flexibility if needed
        # For write_only in TestCaseDetailSerializer, these need to be writable
        extra_kwargs = {
            'action': {'required': True, 'allow_blank': False},
            'expected_result': {'required': True, 'allow_blank': False},
            'step_number': {'required': False} # Usually set programmatically
        }
# --- End TestCaseStepSerializer ---

# --- Add TestCaseVersionSerializer --- 
try:
    from apps.users.serializers import UserSimpleSerializer
except ImportError:
    # Fallback basic definition (as before)
    User = get_user_model()
    class UserSimpleSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ['id', 'username', 'name']
            ref_name = 'TestcasesUserSimple'

class TestCaseVersionSerializer(serializers.ModelSerializer):
    """序列化器，用于测试用例版本"""
    creator_info = UserSimpleSerializer(source='creator', read_only=True, allow_null=True)
    # 可以选择性地包含原始 TestCase 的信息
    # test_case_info = TestCaseSerializer(source='test_case', read_only=True) # 避免循环导入，先不加
    steps = TestCaseStepSerializer(many=True, required=False, read_only=True) # Keep this for reading steps. Mark as read_only if it represents output.

    # 可能需要处理 steps_data 的展示/输入格式
    # 例如，如果前端需要特定的 JSON 结构

    class Meta:
        model = TestCaseVersion
        fields = [
            'id',
            'test_case', # ID of the original TestCase
            'version_number',
            'title',
            'precondition',
            'priority',
            'case_type',
            'method',
            'steps', # Add 'steps' field here for reading
            'steps_data', # Raw JSON steps
            'change_description',
            'creator', 'creator_info',
            'created_at',
            'is_active',
        ]
        # Ensure 'steps' is not in read_only_fields if it should be writable via this serializer,
        # but based on usage (reading active version details), it should be read_only or handled by the field definition.
        # Let's rely on the read_only=True on the field itself for now.
        read_only_fields = ['id', 'test_case', 'version_number', 'creator_info', 'created_at'] # Version number might be set programmatically
# --- End TestCaseVersionSerializer ---

# --- Define a simple version serializer for list view ---
class SimpleTestCaseVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseVersion
        fields = ['id', 'version_number', 'is_active', 'priority', 'case_type'] # Add priority and case_type
# --- End simple version serializer ---

class TestCaseSerializer(serializers.ModelSerializer):
    """测试用例序列化器 (基本信息，用于列表)"""
    module_name = serializers.StringRelatedField(source='module', read_only=True, allow_null=True)
    project_name = serializers.StringRelatedField(source='project', read_only=True)
    created_by_username = serializers.ReadOnlyField(source='created_by.username', allow_null=True)
    updated_by_username = serializers.ReadOnlyField(source='updated_by.username', allow_null=True)
    tags = serializers.SlugRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        slug_field='name'
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Add active version info for list view
    active_version_info = SimpleTestCaseVersionSerializer(source='active_version', read_only=True)
    priority_display = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            'id', 'title', 'module', 'module_name', 'project', 'project_name',
            'status', 'status_display',
            'priority_display',
            'tags',
            'created_by', 'created_by_username', 'updated_by', 'updated_by_username',
            'created_at', 'updated_at',
            'active_version', 'active_version_info' # Include active_version FK and its basic info
        ]
        # active_version is now read_only as it's set when creating/activating versions
        read_only_fields = [
            'id', 'status_display', 'priority_display', 'created_by_username',
            'updated_by_username', 'created_at', 'updated_at', 'active_version',
            'active_version_info', 'project_name', 'module_name'
        ]

    def get_priority_display(self, obj):
        """
        获取优先级的显示文本 (例如: P1 - Blocker)
        """
        priority_map = {
            1: "P1 - Blocker",
            2: "P2 - Critical",
            3: "P3 - Major",
            4: "P4 - Minor",
            5: "P5 - Trivial",
        }
        active_version = getattr(obj, 'active_version', None)
        
        if active_version and hasattr(active_version, 'priority'):
            try:
                # 尝试将版本中的 priority 转换为整数
                priority_int = int(active_version.priority)
                if priority_int in priority_map:
                    return priority_map[priority_int]
                else:
                     # Log invalid integer value if needed
                     logger.warning(f"Version {active_version.id} has priority {priority_int} outside expected range 1-5.")
            except (ValueError, TypeError):
                # 如果转换失败 (例如值为 None 或非数字字符串)，记录警告
                logger.warning(f"Could not convert priority '{active_version.priority}' to integer for version {active_version.id}.")
                pass # 继续执行下面的返回 "N/A"
        
        # 如果没有活动版本，或版本没有 priority 属性，或转换/检查失败，返回 N/A
        return "N/A"

class TestCaseDetailSerializer(TestCaseSerializer):
    """测试用例详细序列化器 (读取时显示活动版本详情)"""
    active_version_info = TestCaseVersionSerializer(source='active_version', read_only=True)

    # Add fields for version creation (will be handled in ViewSet's create)
    # These fields are part of the version, not the TestCase model itself.
    # Mark as write_only so they are accepted in POST/PUT but not expected in output
    # unless explicitly handled.
    precondition = serializers.CharField(max_length=500, required=False, allow_blank=True, write_only=True)
    priority = serializers.CharField(max_length=10, required=True, write_only=True) # Example: P0, P1 etc. From choices.
    case_type = serializers.CharField(max_length=20, required=True, write_only=True) # Example: Functional, Performance. From choices.
    method = serializers.CharField(max_length=20, required=True, write_only=True)   # Example: Manual, Automated. From choices.
    
    # Rename field to 'steps' to match incoming data key, remove source
    steps = TestCaseStepSerializer(many=True, required=False, write_only=True)

    # Add fields for controlling version creation
    create_new_version = serializers.BooleanField(
        write_only=True, 
        required=False, 
        default=False, 
        label=_('创建新版本'), 
        help_text=_('选中表示为本次修改创建一个新的用例版本')
    )
    change_description = serializers.CharField(
        write_only=True, 
        required=False, 
        allow_blank=True, 
        label=_('版本变更说明'),
        style={'base_template': 'textarea.html'}
    )

    class Meta(TestCaseSerializer.Meta):
        # Inherit fields from base, active_version_info is overridden above
        # Update fields list to use 'steps' instead of 'steps_input'
        # Add the new control fields
        fields = TestCaseSerializer.Meta.fields + [
            'precondition', 'priority', 'case_type', 'method', 'steps',
            'create_new_version', 'change_description'
        ]
        read_only_fields = TestCaseSerializer.Meta.read_only_fields

class ModuleSerializer(serializers.ModelSerializer):
    """模块序列化器 (基本信息)"""
    project_name = serializers.StringRelatedField(source='project', read_only=True)
    parent_name = serializers.StringRelatedField(source='parent', read_only=True, allow_null=True)

    class Meta:
        model = Module
        fields = ['id', 'name', 'project', 'project_name', 'parent', 'parent_name', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'project', 'created_at', 'updated_at']

class RecursiveModuleSerializer(serializers.Serializer):
    """用于递归显示模块树的序列化器"""
    def to_representation(self, value):
        serializer = ModuleSerializer(value, context=self.context)
        data = serializer.data
        children = value.children.all()
        if children:
            data['children'] = RecursiveModuleSerializer(children, many=True, context=self.context).data
        # Uncomment to include test cases in the tree view
        # testcases = value.testcases.all()
        # if testcases:
        #     data['testcases'] = TestCaseSerializer(testcases, many=True, context=self.context).data
        return data 