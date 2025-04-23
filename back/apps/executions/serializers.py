from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from .models import TestPlan, TestRun, TestResult, Environment
# Import aggregation functions
from django.db.models import Count, Q 
import logging
from apps.projects.models import Project

# 导入其他 app 的序列化器 (如果存在)
# 假设 UserSimpleSerializer 在 users app, ProjectSimpleSerializer 在 projects app, TestCaseSimpleSerializer 在 testcases app
try:
    from apps.users.serializers import UserSimpleSerializer
except ImportError:
    # 如果 users app 没有 UserSimpleSerializer，定义一个临时的
    User = get_user_model()
    class UserSimpleSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = ['id', 'username', 'name']
            ref_name = 'ExecutionsUserSimple'

try:
    from apps.projects.serializers import ProjectSimpleSerializer
except ImportError:
    # 如果 projects app 没有 ProjectSimpleSerializer，定义一个临时的
    class ProjectSimpleSerializer(serializers.ModelSerializer):
        class Meta:
            model = Project
            fields = ['id', 'name']

try:
    from apps.testcases.serializers import TestCaseSimpleSerializer
except ImportError:
    # 如果 testcases app 没有 TestCaseSimpleSerializer，定义一个临时的
    from apps.testcases.models import TestCase
    class TestCaseSimpleSerializer(serializers.ModelSerializer):
        class Meta:
            model = TestCase
            fields = ['id', 'title']

# Try importing EnvironmentSimpleSerializer or define a fallback
try:
    # Assuming EnvironmentSimpleSerializer is in projects app
    from apps.projects.serializers import EnvironmentSimpleSerializer
except ImportError:
    # Fallback basic definition if not found or apps.projects doesn't exist yet
    class EnvironmentSimpleSerializer(serializers.ModelSerializer):
        class Meta:
            model = Environment # Use the imported Environment model
            fields = ['id', 'name']

# Import TestCaseVersion and the serializer we created
from apps.testcases.models import TestCase, TestCaseVersion
from apps.testcases.serializers import TestCaseVersionSerializer, SimpleTestCaseVersionSerializer

User = get_user_model()

logger = logging.getLogger(__name__)

class TestPlanSerializer(serializers.ModelSerializer):
    """测试计划序列化器 (列表和基本创建/更新)"""
    creator_info = UserSimpleSerializer(source='creator', read_only=True, allow_null=True)
    project_info = ProjectSimpleSerializer(source='project', read_only=True)
    # Use the new field name and a simple version serializer for info
    plan_case_versions_info = SimpleTestCaseVersionSerializer(source='plan_case_versions', many=True, read_only=True)

    # Write field now points to TestCaseVersion
    plan_case_versions = serializers.PrimaryKeyRelatedField(
        queryset=TestCaseVersion.objects.all(), # Query against versions
        many=True,
        write_only=True,
        required=False,
        label=_('包含的测试用例版本')
    )

    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        write_only=True,
        label=_('所属项目')
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = TestPlan
        fields = [
            'id', 'name', 'description',
            'project', 'project_info',
            'creator_info',
            'start_date', 'end_date', 'status', 'status_display', 'is_active',
            'plan_case_versions', # For writing version IDs
            'plan_case_versions_info', # For reading version details
            'created_at', 'updated_at'
        ]
        # Adjust read_only_fields
        read_only_fields = ['creator_info', 'project_info', 'plan_case_versions_info', 'created_at', 'updated_at']

    def validate_plan_case_versions(self, value):
        """检查提供的所有 TestCaseVersion ID 是否都有效存在。"""
        if not value: # Allow empty list
            return value

        # Convert potential list of TestCaseVersion objects back to IDs if needed
        # (though PrimaryKeyRelatedField usually gives IDs)
        incoming_ids = set()
        for item in value:
            if isinstance(item, TestCaseVersion):
                incoming_ids.add(item.pk)
            else:
                try:
                    incoming_ids.add(int(item))
                except (ValueError, TypeError):
                    raise serializers.ValidationError(f"无效的 ID 类型: {item}")

        # Query existing version IDs from the database for the provided IDs
        existing_ids = set(
            TestCaseVersion.objects.filter(pk__in=incoming_ids).values_list('pk', flat=True)
        )

        # Find the difference
        invalid_ids = incoming_ids - existing_ids

        if invalid_ids:
            # Format the error message clearly
            invalid_ids_str = ", ".join(map(str, sorted(list(invalid_ids))))
            raise serializers.ValidationError(
                f"提供的测试用例版本 ID 无效或不存在: {invalid_ids_str}"
            )

        # Return the original value (list of IDs) if all are valid
        # The PrimaryKeyRelatedField itself will handle conversion if objects were passed
        return value

    def create(self, validated_data):
        # Ensure creator is set from context if available
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
             validated_data['creator'] = request.user
        # Handle M2M relation after instance creation
        case_versions = validated_data.pop('plan_case_versions', None)
        instance = super().create(validated_data)
        if case_versions is not None:
            instance.plan_case_versions.set(case_versions)
        return instance

    def update(self, instance, validated_data):
        logger.info(f"[Serializer Update] Called for TestPlan ID: {instance.id}")
        logger.debug(f"[Serializer Update] Validated data BEFORE pop: {validated_data}")
        case_versions = validated_data.pop('plan_case_versions', None)
        logger.info(f"[Serializer Update] Popped plan_case_versions: {case_versions}")
        
        # Update other fields first
        instance = super().update(instance, validated_data)
        logger.info(f"[Serializer Update] Instance updated (before M2M set) for ID: {instance.id}")
        
        if case_versions is not None:
            logger.info(f"[Serializer Update] Attempting to set plan_case_versions to {case_versions} for ID: {instance.id}")
            try:
                # Use a database transaction potentially? Although .set() should handle this.
                instance.plan_case_versions.set(case_versions)
                # It's generally good practice to save the instance IF M2M changes *might* affect other fields 
                # or if signals rely on the M2M being set before final save, 
                # but .set() directly modifies the M2M table, so explicit save *might* not be needed here.
                # instance.save() # Let's try without explicit save first, as super().update already saved.
                logger.info(f"[Serializer Update] Successfully called .set() for plan_case_versions for ID: {instance.id}")
                # Verify the content AFTER setting it
                current_related_ids = list(instance.plan_case_versions.values_list('id', flat=True))
                logger.info(f"[Serializer Update] Current related plan_case_versions IDs after set: {current_related_ids} for ID: {instance.id}")
            except Exception as e:
                logger.error(f"[Serializer Update] Error setting plan_case_versions for ID: {instance.id}: {e}", exc_info=True)
        else:
             logger.info(f"[Serializer Update] case_versions was None, skipping M2M set for ID: {instance.id}.")
             
        return instance

class TestRunSerializer(serializers.ModelSerializer):
    """测试执行轮次序列化器 (用于列表和基础操作)"""
    # Read-only fields for display
    test_plan_info = TestPlanSerializer(source='test_plan', read_only=True)
    project_info = ProjectSimpleSerializer(source='project', read_only=True)
    environment_info = EnvironmentSimpleSerializer(source='environment', read_only=True, allow_null=True)
    assignee_info = UserSimpleSerializer(source='assignee', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # Add progress field
    progress = serializers.SerializerMethodField(read_only=True)

    # Writable fields for relationships
    test_plan = serializers.PrimaryKeyRelatedField(
        queryset=TestPlan.objects.all(), 
        write_only=True, 
        required=False
    )
    environment = serializers.PrimaryKeyRelatedField(queryset=Environment.objects.all(), allow_null=True, required=False, write_only=True)
    assignee = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False, write_only=True)

    class Meta:
        model = TestRun
        fields = [
            'id', 'name', 'description',
            'test_plan', 'test_plan_info',
            'project_info',
            'status', 'status_display',
            'environment', 'environment_info',
            'assignee', 'assignee_info',
            'start_time', 'end_time',
            'progress',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'project_info', 'test_plan_info', 'environment_info', 'assignee_info',
            'created_at', 'updated_at', 'status_display',
            'progress'
        ]

    def get_progress(self, obj):
        """计算单个 TestRun 的执行进度百分比"""
        total = 0
        executed = 0
        try:
            # 优先使用预取的结果 (如果可用)
            if hasattr(obj, '_prefetched_objects_cache') and 'results' in obj._prefetched_objects_cache:
                results_qs = obj._prefetched_objects_cache['results']
                total = len(results_qs)
                executed = sum(1 for r in results_qs if r.status != 'untested')
                # logger.debug(f"使用预取数据计算进度 TestRun {obj.id}: total={total}, executed={executed}")
            else:
                # 如果没有预取，则回退查询 (效率较低)
                # logger.warning(f"通过单独查询计算进度 TestRun {obj.id}。考虑 prefetch_related('results').")
                summary = TestResult.objects.filter(test_run=obj).aggregate(
                    total=Count('id'),
                    executed=Count('id', filter=~Q(status='untested'))
                )
                total = summary.get('total', 0)
                executed = summary.get('executed', 0)
        except Exception as e:
            logger.error(f"计算 TestRun {obj.id} 进度时出错: {e}", exc_info=True)
            return 0 # 计算出错时返回 0

        if total > 0:
            return round((executed / total) * 100)
        return 0

    def create(self, validated_data):
        test_plan = validated_data.get('test_plan')
        project = None
        if test_plan:
            project = test_plan.project
            validated_data['project'] = project
        else:
            # Consider raising an error if test_plan is mandatory for creating a run
            pass

        # First, create the TestRun instance
        test_run = super().create(validated_data)

        return test_run

    def update(self, instance, validated_data):
        # Update project if test_plan changes (though changing plan might be restricted)
        if 'test_plan' in validated_data:
            instance.project = validated_data['test_plan'].project
        return super().update(instance, validated_data)

class TestResultSerializer(serializers.ModelSerializer):
    """测试结果序列化器"""
    # Read-only fields for displaying related object info
    test_run_name = serializers.StringRelatedField(source='test_run', read_only=True)
    # Revert to testcase_version_info and ensure source points to the model field
    testcase_version_info = TestCaseVersionSerializer(source='testcase_version', read_only=True) # Reverted name
    executor_info = UserSimpleSerializer(source='executor', read_only=True, allow_null=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    # Allow setting FKs by ID on write operations, pointing to TestCaseVersion
    test_run = serializers.PrimaryKeyRelatedField(queryset=TestRun.objects.all())
    # Revert to testcase_version, ensuring source is correct (usually model field name)
    testcase_version = serializers.PrimaryKeyRelatedField(queryset=TestCaseVersion.objects.all()) # Reverted name, source might not be needed if field name matches
    executor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    class Meta:
        model = TestResult
        fields = [
            'id',
            'test_run', 'test_run_name',
            'testcase_version', # Reverted name
            'testcase_version_info', # Reverted name
            'status', 'status_display',
            'executor', 'executor_info',
            'executed_at', 'duration',
            'comments', 'bug_id'
        ]
        read_only_fields = [
             'id', 'test_run_name', 
             'testcase_version_info', # Reverted name
             'executor_info', 'status_display'
        ]

    # Automatically set executor and executed_at on update if status changes to a final state
    def update(self, instance, validated_data):
        request = self.context.get('request')
        current_status = instance.status
        new_status = validated_data.get('status', current_status)

        # Set executor only if provided or if status changes from untested and user is available
        if not validated_data.get('executor'):
             if current_status == 'untested' and new_status != 'untested' and request and hasattr(request, 'user'):
                 validated_data['executor'] = request.user

        # Set executed_at only if status changes to a final state and not already set
        if not validated_data.get('executed_at'):
             final_statuses = ['passed', 'failed', 'skipped', 'blocked']
             if new_status in final_statuses and current_status not in final_statuses:
                 from django.utils import timezone
                 validated_data['executed_at'] = timezone.now()

        return super().update(instance, validated_data)

# Define TestRunDetailSerializer inheriting from TestRunSerializer
class TestRunDetailSerializer(TestRunSerializer):
    """测试执行轮次详细序列化器，不再包含结果列表 (结果将单独获取)"""
    # Remove nested serializer for results
    # results = TestResultSerializer(many=True, read_only=True)

    class Meta(TestRunSerializer.Meta):
        # Inherit fields from the base TestRunSerializer
        # Remove 'results' from the list
        fields = TestRunSerializer.Meta.fields # Keep only base fields
        # Inherit read_only_fields if necessary, or define specific ones
        # Remove 'results' from read_only fields
        read_only_fields = TestRunSerializer.Meta.read_only_fields 