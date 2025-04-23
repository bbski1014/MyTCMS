from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import TestPlan, TestRun, TestResult
from .serializers import TestPlanSerializer, TestRunSerializer, TestResultSerializer, TestRunDetailSerializer
# 导入权限类 (如果需要自定义)
# from .permissions import IsProjectMemberOrAdmin # 示例
# Import TestCase model
from apps.testcases.models import TestCase 
# Import Response and status from rest_framework
from rest_framework import status
# Import transaction for atomicity
from django.db import transaction
# Import aggregation functions
from django.db.models import Count, Q
# Import timezone
from django.utils import timezone

class TestPlanViewSet(viewsets.ModelViewSet):
    """
    测试计划视图集
    提供测试计划的 CRUD 操作。
    """
    queryset = TestPlan.objects.select_related('project', 'creator').all()
    serializer_class = TestPlanSerializer
    # 权限控制: 至少需要登录才能访问
    permission_classes = [permissions.IsAuthenticated] # 可以根据需要调整，例如只有管理员或项目成员才能创建/修改

    # 添加筛选和排序功能
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'creator'] # 允许按项目、状态、创建人筛选
    search_fields = ['name', 'description'] # 允许按名称、描述搜索
    ordering_fields = ['name', 'status', 'created_at', 'start_date', 'end_date'] # 允许排序的字段
    ordering = ['-created_at'] # 默认排序

    # 如果需要根据用户角色或项目成员身份进行更细粒度的权限控制，可以重写 get_permissions 方法
    # def get_permissions(self):
    #     if self.action in ['create', 'update', 'partial_update', 'destroy']:
    #         # 示例：只允许管理员或特定项目角色操作
    #         return [permissions.IsAdminUser()] # 或者自定义权限
    #     return [permissions.IsAuthenticated()]

    # --- 后续可以添加管理计划中测试用例的 action ---
    # @action(detail=True, methods=['get', 'post'])
    # def cases(self, request, pk=None):
    #     """获取或向测试计划添加/更新用例"""
    #     test_plan = self.get_object()
    #     if request.method == 'GET':
    #         # 获取计划下的所有用例
    #         plan_cases = TestPlanCase.objects.filter(test_plan=test_plan).select_related('test_case', 'assigned_to')
    #         serializer = TestPlanCaseSerializer(plan_cases, many=True)
    #         return Response(serializer.data)
    #     elif request.method == 'POST':
    #         # 批量添加或更新用例
    #         # ... 实现批量处理逻辑 ...
    #         pass

    # @action(detail=True, methods=['delete'], url_path='cases/(?P<case_pk>[^/.]+)')
    # def remove_case(self, request, pk=None, case_pk=None):
    #     """从测试计划中移除特定用例"""
    #     test_plan = self.get_object()
    #     # ... 实现移除逻辑 ...
    #     pass
    # --- 结束用例管理 action ---

# --- Add TestRunViewSet --- 
class TestRunViewSet(viewsets.ModelViewSet):
    """测试执行轮次视图集"""
    # Use select_related for FKs on TestRun itself
    # Use prefetch_related for reverse FKs (results) and nested relations
    queryset = TestRun.objects.select_related(
        'test_plan', 'project', 'environment', 'assignee' # Removed 'created_by'
    ).prefetch_related(
        'results',                         
        'results__testcase_version',       # <<< Use the correct model field name
        'results__testcase_version__test_case', # <<< Use the correct model field name
        'results__testcase_version__steps', # <<< Use the correct model field name
        'results__executor'                
    ).all()
    # serializer_class = TestRunSerializer # Set dynamically by get_serializer_class
    permission_classes = [permissions.IsAuthenticated] 
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'test_plan', 'status', 'environment', 'assignee']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'status', 'created_at', 'start_time', 'end_time']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """根据 action 返回不同的序列化器"""
        if self.action == 'retrieve':
            return TestRunDetailSerializer # Use detail serializer for retrieve action
        # For list, create, update, partial_update, use the base serializer
        return TestRunSerializer
    
    # Add get_serializer_context if not already present
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    # Override create method to add TestResult generation logic
    @transaction.atomic # Ensure atomicity: either all succeed or all fail
    def create(self, request, *args, **kwargs):
        """创建 TestRun 并自动生成关联的 TestResult 记录"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Manually fetch the TestPlan to get project and cases
        try:
            test_plan = TestPlan.objects.select_related('project').prefetch_related('plan_case_versions').get(id=serializer.validated_data.get('test_plan').id)
        except TestPlan.DoesNotExist:
            return Response({"test_plan": ["无效的测试计划 ID"]}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create the TestRun instance, ensuring the project is set correctly
        test_run = serializer.save(project=test_plan.project)

        # Now, create TestResult objects based on the test plan case *versions*
        testcase_versions_in_plan = test_plan.plan_case_versions.all()
        results_to_create = []
        # Use a set to track added *TestCaseVersion* IDs for de-duplication
        added_case_version_ids = set()
        for case_version in testcase_versions_in_plan:
            if case_version.id not in added_case_version_ids:
                results_to_create.append(
                    TestResult(
                        test_run=test_run,
                        testcase_version=case_version, # Use the correct foreign key field
                        status='untested' # Default status from the model
                    )
                )
                added_case_version_ids.add(case_version.id)

        # --- 恢复使用 bulk_create --- 
        if results_to_create:
            # Consider adding ignore_conflicts=True for extra safety, though de-duplication should handle it
            TestResult.objects.bulk_create(results_to_create, ignore_conflicts=True)
        # --- 结束恢复 ---

        # Return the serialized TestRun data
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # --- Add summary action here --- 
    @action(detail=True, methods=['get'], url_path='summary')
    def summary(self, request, pk=None):
        """
        获取单个测试执行轮次的统计摘要信息。
        """
        test_run = self.get_object() # 获取 TestRun 实例

        # 使用聚合查询计算各种状态的数量
        summary_data = TestResult.objects.filter(test_run=test_run).aggregate(
            total=Count('id'),
            passed=Count('id', filter=Q(status='passed')),
            failed=Count('id', filter=Q(status='failed')),
            blocked=Count('id', filter=Q(status='blocked')),
            skipped=Count('id', filter=Q(status='skipped')),
            untested=Count('id', filter=Q(status='untested')),
            # 计算已执行的数量 (非 untested)
            executed=Count('id', filter=~Q(status='untested'))
        )

        # 计算进度百分比
        total = summary_data.get('total', 0)
        executed = summary_data.get('executed', 0)
        progress = 0
        if total > 0:
            progress = round((executed / total) * 100)

        # 添加进度到摘要数据
        summary_data['progress'] = progress

        return Response(summary_data)

    # --- End summary action --- 

    # --- TODO: Add actions for managing testcases in a run --- 
    # Example: @action(detail=True, methods=['post'])
    # def add_cases(self, request, pk=None): ...

    # --- TODO: Add action for getting run progress/summary --- 
    # Example: @action(detail=True, methods=['get'])
    # def summary(self, request, pk=None): ...

# --- Add TestResultViewSet --- 
class TestResultViewSet(viewsets.ModelViewSet):
    """测试结果视图集 (基础)

    注意: 创建和更新结果通常通过 TestRunViewSet 的 Action 或嵌套路由处理，
    这个独立的 ViewSet 主要用于查询和可能的独立管理。
    """
    queryset = TestResult.objects.select_related(
        'test_run', 'testcase_version', 'executor'
    ).prefetch_related(
        'testcase_version__test_case' # Add prefetch for test case title
    ).all()
    serializer_class = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['test_run', 'testcase_version', 'status', 'executor', 'bug_id']
    search_fields = ['testcase_version__title', 'comments', 'bug_id']
    ordering_fields = ['executed_at', 'status']
    ordering = ['-executed_at']

    @action(detail=False, methods=['post'], url_path='bulk-update')
    @transaction.atomic # 确保操作的原子性
    def bulk_update(self, request, *args, **kwargs):
        """
        批量更新测试结果的状态。
        请求体需要包含:
        - ids: 一个包含 TestResult ID 的列表。
        - status: 目标状态字符串。
        - (可选) comments: 要批量设置的备注。
        - (可选) bug_id: 要批量设置的 Bug ID。
        """
        ids = request.data.get('ids')
        new_status = request.data.get('status')
        new_comments = request.data.get('comments', None) # 可选
        new_bug_id = request.data.get('bug_id', None)     # 可选

        # --- 输入验证 ---
        if not isinstance(ids, list) or not ids:
            return Response({"error": "参数 'ids' 必须是一个非空的列表。"}, status=status.HTTP_400_BAD_REQUEST)
        if not new_status:
            return Response({"error": "必须提供 'status' 参数。"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证 status 是否是有效选项 (从 TestResult 模型获取)
        valid_statuses = [choice[0] for choice in TestResult.STATUS_CHOICES]
        if new_status not in valid_statuses:
             return Response({"error": f"无效的状态 '{new_status}'。有效选项为: {', '.join(valid_statuses)}"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证 ID 列表中的所有 ID 都是有效的整数
        try:
            valid_ids = [int(id_val) for id_val in ids]
        except (ValueError, TypeError):
             return Response({"error": "参数 'ids' 列表必须只包含有效的整数 ID。"}, status=status.HTTP_400_BAD_REQUEST)

        # --- 获取需要更新的对象 --- 
        # 注意：这里不过滤 test_run，允许跨 run 更新？或者应该加过滤？
        # 考虑到 API 路径是 /testresults/bulk-update/，不过滤似乎更通用。
        # 如果需要限制在某个 run 内，前端调用时需要确保 ids 都来自同一个 run。
        queryset = self.get_queryset().filter(id__in=valid_ids)
        
        # 检查是否有无效的 ID (请求的 ID 数量和实际找到的是否一致)
        if queryset.count() != len(valid_ids):
             found_ids = set(queryset.values_list('id', flat=True))
             missing_ids = set(valid_ids) - found_ids
             # 记录警告，但继续执行
             print(f"Warning: Bulk update requested for IDs {valid_ids}, but missing IDs: {list(missing_ids)}")

        # --- 准备更新数据 --- 
        update_data = {'status': new_status}
        current_time = timezone.now()
        executor = request.user if request.user.is_authenticated else None
        
        if new_comments is not None:
            update_data['comments'] = new_comments
        if new_bug_id is not None:
            update_data['bug_id'] = new_bug_id
            
        # --- 处理自动字段 (executor 和 executed_at) ---
        final_statuses = ['passed', 'failed', 'skipped', 'blocked']
        results_to_update_auto_fields = []
        if executor:
             # 获取那些状态从未测试变为其他，或者从非最终变为最终，并且当前 executor 为空的 ID
             results_needing_auto_update = queryset.filter(
                 (Q(status='untested') & ~Q(status=new_status)) | 
                 (~Q(status__in=final_statuses) & Q(status=new_status) & Q(status__in=final_statuses))
             ).filter(executor__isnull=True).values_list('id', flat=True)
             
             results_to_update_auto_fields = list(results_needing_auto_update)

        # --- 执行更新 --- 
        # 1. 先批量更新主要字段 (status, comments, bug_id)
        updated_count = queryset.update(**update_data)
        
        # 2. 再单独更新需要自动设置 executor 和 executed_at 的记录
        auto_update_count = 0
        if results_to_update_auto_fields: 
             auto_update_count = TestResult.objects.filter(id__in=results_to_update_auto_fields).update(
                 executor=executor, 
                 executed_at=current_time
             )
        
        return Response({
            "message": f"成功更新了 {updated_count} 条记录。",
            "auto_fields_updated": auto_update_count
        }, status=status.HTTP_200_OK)

    # --- TODO: Override create/update or remove write methods --- 
    # Typically, results are created/updated in the context of a TestRun.
    # Consider making this ReadOnlyModelViewSet or customizing write methods.
