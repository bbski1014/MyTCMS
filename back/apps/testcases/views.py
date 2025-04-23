from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
# Add required imports
from django.db import transaction
from django.utils import timezone
# Remove TestStep import as it's commented out in models.py
from .models import Module, Tag, TestCase, TestCaseVersion, TestCaseStep # Make sure all are imported
# Import project permissions
from apps.projects.permissions import IsProjectMember, IsProjectManager
from .serializers import (
    ModuleSerializer, TagSerializer, TestCaseSerializer, 
    TestCaseDetailSerializer, RecursiveModuleSerializer, TestCaseStepSerializer,
    TestCaseVersionSerializer # Add TestCaseVersionSerializer import
)
import logging

logger = logging.getLogger(__name__) # 新增：获取 logger 实例

# Create your views here.

class TagViewSet(viewsets.ModelViewSet):
    """标签视图集"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = None # No pagination for tags

class ModuleViewSet(viewsets.ModelViewSet):
    """模块视图集"""
    serializer_class = ModuleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """根据 URL 中的 project_pk 过滤模块"""
        project_pk = self.kwargs.get('project_pk') 
        queryset = Module.objects.select_related('project', 'parent').filter(project_id=project_pk)
        return queryset

    def perform_create(self, serializer):
        """创建模块时自动关联 URL 中的项目 ID"""
        project_pk = self.kwargs.get('project_pk')
        serializer.save(project_id=project_pk)

    def get_permissions(self):
        """根据操作动态设置权限"""
        if self.action in ['list', 'retrieve', 'get_module_tree']:
            return [IsProjectMember()] 
        return [IsProjectManager()]

    @action(detail=False, methods=['get'], url_path='tree')
    def get_module_tree(self, request, project_pk=None):
        if not project_pk:
            return Response({"error": "无法从 URL 获取项目 ID"}, status=status.HTTP_400_BAD_REQUEST)
        
        root_modules = Module.objects.filter(project_id=project_pk, parent__isnull=True)
        serializer = RecursiveModuleSerializer(root_modules, many=True, context={'request': request})
        return Response(serializer.data)

class TestCaseViewSet(viewsets.ModelViewSet):
    """测试用例视图集"""
    queryset = TestCase.objects.select_related(
        'module', 'project', 'created_by', 'updated_by', 
        'active_version' # Add active_version to select_related for efficiency
    ).prefetch_related(
        'tags', 
        # 'steps', # Prefetching TestCase.steps might be unnecessary now
        'active_version__steps',  # Prefetch steps related to the active version
        'active_version__creator' # Prefetch creator for active_version_info
    ).all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # Define filterset_fields more explicitly for better control
    filterset_fields = {
        'project': ['exact'],
        'module': ['exact', 'isnull'], # Allow filtering for cases without module
        'status': ['exact', 'in'],
        'tags__name': ['exact', 'in'], # Filter by tag names
        'created_by': ['exact'],
        'created_at': ['date', 'date__gte', 'date__lte', 'date__range'], # More date filters
        'updated_at': ['date', 'date__gte', 'date__lte', 'date__range'],
    }
    search_fields = ['title', 'tags__name']
    ordering_fields = [
        'id', # 新增：按 ID 排序
        'title', 
        'status', 
        'created_at', 
        'updated_at',
        'created_by__username', # 新增：按创建人用户名排序
        'active_version__priority' # 新增：按活动版本的优先级排序
    ]
    ordering = ['-updated_at']

    def get_permissions(self):
        """根据操作动态设置权限"""
        if self.action in ['list', 'retrieve']:
            # 查看用例列表、详情，只需要是项目成员
            return [IsProjectMember()]
        # 创建、更新、删除用例，需要项目经理权限 (或根据需要调整为 Tester 等角色)
        # 暂时先设置为项目经理
        return [IsProjectManager()]

    def get_serializer_class(self):
        if self.action == 'list':
            return TestCaseSerializer
        # Use detail serializer for create/retrieve/update/partial_update
        return TestCaseDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    # Override create method for version handling
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Extract TestCase data (fields present in TestCase model)
        test_case_data = {
            'project': validated_data.get('project'),
            'module': validated_data.get('module'),
            'title': validated_data.get('title'),
            'status': validated_data.get('status', 'Draft'),
            # created_by and updated_by will be set automatically
        }
        tags_data = validated_data.pop('tags', []) # Get tags separately

        # Extract TestCaseVersion data (write_only fields + title)
        version_data = {
            'title': validated_data.get('title'),
            'precondition': validated_data.get('precondition', ''),
            'priority': validated_data.get('priority'),
            'case_type': validated_data.get('case_type'),
            'method': validated_data.get('method'),
            # 'change_description': 'Initial version created.', # Optional description
            'creator': request.user,
            'version_number': 1,
            'is_active': True,
        }
        
        # Extract steps data using the corrected field name 'steps'
        steps_data = validated_data.get('steps', []) # Use 'steps' now

        # 1. Create TestCase instance
        test_case = TestCase.objects.create(
            **test_case_data,
            created_by=request.user,
            updated_by=request.user
        )

        # 2. Create TestCaseVersion instance linked to the TestCase
        version_data['test_case'] = test_case
        test_case_version = TestCaseVersion.objects.create(**version_data)

        # 3. Create TestCaseStep instances linked to the TestCaseVersion
        if steps_data:
            steps_to_create = [
                TestCaseStep(
                    version=test_case_version,
                    step_number=idx + 1,
                    action=step.get('action', ''), # Add default empty string
                    expected_result=step.get('expected_result', '') # Add default empty string
                ) for idx, step in enumerate(steps_data)
            ]
            TestCaseStep.objects.bulk_create(steps_to_create)

            # Store the structured steps_data in the version's JSON field as well
            test_case_version.steps_data = steps_data
            test_case_version.save(update_fields=['steps_data'])

        # 4. Update TestCase's active_version
        test_case.active_version = test_case_version
        test_case.save(update_fields=['active_version', 'updated_at', 'updated_by']) # Also update updated_by

        # 5. Set Tags for TestCase
        if tags_data:
            test_case.tags.set(tags_data)

        # 6. Serialize the created TestCase instance using the detail serializer
        response_serializer = self.get_serializer(test_case)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object() # Get the TestCase instance

        serializer = self.get_serializer(instance, data=request.data, partial=partial) # Pass partial correctly
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        create_new = validated_data.get('create_new_version', False)
        change_desc = validated_data.get('change_description', '')

        if create_new:
            # --- Logic to create a new version (adapted from existing code) ---
            current_active_version = instance.active_version # Get current active version

            # Determine next version number and if old version needs deactivation
            if current_active_version:
                next_version_number = current_active_version.version_number + 1
                deactivate_old_version = True
                # Use current active version title as fallback if not provided in request
                title_fallback = current_active_version.title 
            else:
                # Handle case where no active version exists (treat as first version)
                logger.info(f"No active version found for TestCase {instance.id}. Creating version 1.")
                next_version_number = 1
                deactivate_old_version = False # Nothing to deactivate
                # Use instance title as fallback if no active version ever existed
                title_fallback = instance.title

            # Extract data for the new version (including priority validation)
            priority_value = validated_data.get('priority')
            valid_priority = None
            if priority_value is not None and priority_value != '':
                try:
                    priority_int = int(priority_value)
                    if 1 <= priority_int <= 5:
                       valid_priority = priority_int
                    else:
                        logger.warning(f"Invalid priority value received: {priority_value}. Must be between 1 and 5.")
                except (ValueError, TypeError):
                    logger.warning(f"Could not convert priority '{priority_value}' to integer.")
            else:
                logger.info(f"Priority value received is empty or None: {priority_value}")
                
            new_version_data = {
                'test_case': instance,
                'version_number': next_version_number, # Use calculated version number
                'title': validated_data.get('title', title_fallback), # Use validated title or fallback
                'precondition': validated_data.get('precondition', ''),
                'priority': valid_priority, # Use validated priority
                'case_type': validated_data.get('case_type'),
                'method': validated_data.get('method'),
                'change_description': change_desc,
                'creator': request.user,
                'is_active': True,
            }
            new_steps_input = validated_data.get('steps', [])

            # 1. Create the new TestCaseVersion
            new_version = TestCaseVersion.objects.create(**new_version_data)

            # 2. Create new TestCaseSteps for the new version
            if new_steps_input:
                steps_to_create = [
                    TestCaseStep(
                        version=new_version,
                        step_number=idx + 1,
                        action=step.get('action', ''),
                        expected_result=step.get('expected_result', '')
                    ) for idx, step in enumerate(new_steps_input)
                ]
                TestCaseStep.objects.bulk_create(steps_to_create)
                new_version.steps_data = new_steps_input
                new_version.save(update_fields=['steps_data'])

            # 3. Deactivate the old version *if it existed*
            if deactivate_old_version and current_active_version: # Check both flags
                current_active_version.is_active = False
                current_active_version.save(update_fields=['is_active'])

            # 4. Update the TestCase instance
            instance.active_version = new_version
            instance.updated_by = request.user
            instance.status = validated_data.get('status', instance.status)
            instance.module = validated_data.get('module', instance.module)
            instance.title = new_version.title # Sync TestCase title with new version title
            update_fields_tc = ['active_version', 'updated_by', 'updated_at', 'status', 'module', 'title']
            instance.save(update_fields=update_fields_tc)

            # 5. Handle tags separately
            if 'tags' in validated_data:
                instance.tags.set(validated_data['tags'])

            response_serializer = self.get_serializer(instance)
            return Response(response_serializer.data)

        else:
            # --- Logic to update ONLY TestCase metadata (no new version) ---
            # Ensure version content fields are not accidentally updated
            allowed_tc_fields = ['status', 'module', 'tags'] # Define allowed fields explicitly
            has_metadata_changes = False
            update_fields_metadata = ['updated_by', 'updated_at']

            if 'status' in validated_data and validated_data['status'] != instance.status:
                instance.status = validated_data['status']
                update_fields_metadata.append('status')
                has_metadata_changes = True

            if 'module' in validated_data and validated_data['module'] != instance.module:
                instance.module = validated_data['module']
                update_fields_metadata.append('module')
                has_metadata_changes = True

            # Handle tags separately as it's M2M
            if 'tags' in validated_data:
                 # Compare tag sets if possible, or just always set if provided
                 # Getting current tags might involve DB query, weigh performance vs accuracy
                 current_tags = set(instance.tags.all())
                 new_tags = set(validated_data['tags'])
                 if current_tags != new_tags:
                     instance.tags.set(validated_data['tags'])
                     has_metadata_changes = True # Tag change means metadata changed

            if has_metadata_changes:
                instance.updated_by = request.user
                instance.save(update_fields=update_fields_metadata)

            # Return the current state (no content changes applied)
            response_serializer = self.get_serializer(instance)
            return Response(response_serializer.data)

    @action(detail=True, methods=['get'], url_path='versions')
    def versions(self, request, pk=None):
        """获取指定测试用例的版本历史记录"""
        test_case = self.get_object() # Get the specific TestCase instance using pk
        # Query all versions for this test case, ordered by version number descending
        version_queryset = TestCaseVersion.objects.filter(test_case=test_case).order_by('-version_number')
        
        # Apply pagination
        page = self.paginate_queryset(version_queryset)
        if page is not None:
            serializer = TestCaseVersionSerializer(page, many=True, context=self.get_serializer_context())
            return self.get_paginated_response(serializer.data)

        # If pagination is not enabled or used
        serializer = TestCaseVersionSerializer(version_queryset, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-delete', permission_classes=[IsProjectManager]) # 添加权限控制
    def bulk_delete(self, request):
        """批量删除测试用例"""
        ids_to_delete = request.data.get('ids', [])
        if not isinstance(ids_to_delete, list) or not ids_to_delete:
            return Response({'detail': '请提供要删除的测试用例 ID 列表。'}, status=status.HTTP_400_BAD_REQUEST)

        # 可以在这里添加额外的权限检查，例如检查用户是否有权限删除这些 ID 对应的项目中的用例
        # project_ids = set(TestCase.objects.filter(id__in=ids_to_delete).values_list('project_id', flat=True))
        # for project_id in project_ids:
        #    if not user_has_permission_for_project(request.user, project_id):
        #        return Response({'detail': '权限不足，无法删除某些用例。'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # 检查提供的 ID 是否都是数字
            valid_ids = [int(id_val) for id_val in ids_to_delete]
        except (ValueError, TypeError):
            return Response({'detail': '提供的 ID 列表中包含无效值。'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset() # 获取基础查询集以应用可能的默认过滤
        # 注意：确保 get_queryset() 不会因为 project 过滤导致无法删除其他项目下的用例（如果允许跨项目删除）
        # 如果 ViewSet 与特定项目绑定，批量删除通常也应限于该项目。
        # 如果需要严格限制在特定项目，可以在此加 project 过滤。
        # project_pk = request.query_params.get('project') # 或从其他地方获取项目上下文
        # if project_pk:
        #     queryset = queryset.filter(project_id=project_pk)
        
        deleted_count, _ = queryset.filter(id__in=valid_ids).delete()

        if deleted_count == 0 and len(valid_ids) > 0:
            # 如果提供了有效 ID 但没有删除任何内容，可能 ID 不存在或不符合查询集过滤条件
            return Response({'detail': f'未找到或无法删除指定的测试用例。删除了 {deleted_count} 个用例。'}, status=status.HTTP_404_NOT_FOUND) 

        logger.info(f"用户 {request.user.username} 批量删除了 {deleted_count} 个测试用例，IDs: {valid_ids}")
        return Response({'detail': f'成功删除了 {deleted_count} 个测试用例。'}, status=status.HTTP_200_OK) # 或者使用 204 No Content

    @action(detail=False, methods=['post'], url_path='bulk-update-status', permission_classes=[IsProjectManager])
    def bulk_update_status(self, request):
        """批量修改测试用例的状态"""
        ids_to_update = request.data.get('ids', [])
        target_status = request.data.get('status', None)

        # 1. 验证输入
        if not isinstance(ids_to_update, list) or not ids_to_update:
            return Response({'detail': '请提供要更新的测试用例 ID 列表。'}, status=status.HTTP_400_BAD_REQUEST)
        if not target_status:
            return Response({'detail': '请提供目标状态。'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 验证目标状态是否有效
        valid_statuses = [choice[0] for choice in TestCase.STATUS_CHOICES]
        if target_status not in valid_statuses:
            return Response({'detail': f'无效的状态值: {target_status}。有效值为: {", ".join(valid_statuses)}'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 验证 ID 列表
        try:
            valid_ids = [int(id_val) for id_val in ids_to_update]
        except (ValueError, TypeError):
            return Response({'detail': '提供的 ID 列表中包含无效值。'}, status=status.HTTP_400_BAD_REQUEST)

        # 4. 执行批量更新
        queryset = self.get_queryset()
        updated_count = queryset.filter(id__in=valid_ids).update(
            status=target_status, 
            updated_at=timezone.now(), # 手动更新 updated_at
            updated_by=request.user   # 手动更新 updated_by
        )

        if updated_count == 0 and len(valid_ids) > 0:
            return Response({'detail': f'未找到或无需更新指定的测试用例（可能状态已是目标状态或 ID 不存在）。更新了 {updated_count} 个用例。'}, status=status.HTTP_404_NOT_FOUND)

        logger.info(f"用户 {request.user.username} 批量将 {updated_count} 个测试用例状态更新为 '{target_status}'，IDs: {valid_ids}")
        return Response({'detail': f'成功将 {updated_count} 个测试用例的状态更新为 {target_status}。'}, status=status.HTTP_200_OK)

# --- Add a ViewSet specifically for TestCaseVersion ---

class TestCaseVersionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    测试用例版本视图集 (只读)
    用于获取版本列表 (可按项目过滤) 和版本详情。
    """
    serializer_class = TestCaseVersionSerializer
    permission_classes = [IsProjectMember] # Allow project members to view versions
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        # Filter by the related TestCase's project ID
        'test_case__project': ['exact'], 
        'is_active': ['exact'],
        'creator': ['exact'],
        'created_at': ['date', 'date__gte', 'date__lte', 'date__range'],
    }
    search_fields = ['title', 'test_case__title'] # Search in version title or original case title
    ordering_fields = ['version_number', 'created_at']
    ordering = ['-created_at'] # Default ordering

    def get_queryset(self):
        """
        Base queryset, select/prefetch related for efficiency.
        Filtering by project happens via filterset_fields.
        """
        # Correct filtering: Filter by project ID passed in query params
        queryset = TestCaseVersion.objects.select_related(
            'test_case', 
            'test_case__project', # Needed for project context and possibly permissions
            'creator'
        ).prefetch_related(
            'steps' # Prefetch steps for detail view
        ).all()

        # Apply project filtering based on query parameter if provided
        # The DjangoFilterBackend handles this automatically via filterset_fields
        # project_id = self.request.query_params.get('project') 
        # if project_id:
        #     queryset = queryset.filter(test_case__project_id=project_id)
        
        return queryset
