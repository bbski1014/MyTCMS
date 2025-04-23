from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Project, ProjectTag, ProjectMember, Milestone, Environment, ProjectDocument
from .serializers import (
    ProjectSerializer, ProjectCreateSerializer, ProjectDetailSerializer, ProjectBriefSerializer,
    ProjectTagSerializer, ProjectMemberSerializer, ProjectMemberCreateSerializer,
    MilestoneSerializer, EnvironmentSerializer, ProjectDocumentSerializer
)
from .permissions import IsProjectMember, IsProjectManager, HasProjectPermission


class ProjectTagViewSet(viewsets.ModelViewSet):
    """项目标签视图集"""
    queryset = ProjectTag.objects.all()
    serializer_class = ProjectTagSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


class ProjectViewSet(viewsets.ModelViewSet):
    """项目视图集"""
    queryset = Project.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'manager']
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date', 'name', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        elif self.action == 'retrieve':
            return ProjectDetailSerializer
        elif self.action == 'list':
            return ProjectBriefSerializer
        return ProjectSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [HasProjectPermission('can_manage_project')]
        elif self.action in ['my_projects', 'all_projects']:
            return [permissions.IsAuthenticated()]
        return [IsProjectMember()]
    
    def get_queryset(self):
        """根据用户权限获取项目列表"""
        user = self.request.user
        
        # 处理 AnonymousUser (例如 drf-yasg 生成文档时) 或未认证用户
        if not user or not user.is_authenticated:
            return Project.objects.none() # 返回空查询集
            
        # 管理员可以查看所有项目
        if user.is_staff:
            return Project.objects.all()
        
        # 普通用户只能查看自己参与的项目
        return Project.objects.filter(members__user=user, members__is_active=True).distinct()
    
    def perform_create(self, serializer):
        """创建项目时设置创建者"""
        serializer.save(creator=self.request.user)
    
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """获取当前用户参与的项目"""
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # 获取用户参与的项目
        queryset = Project.objects.filter(members__user=user, members__is_active=True).distinct()
        
        # 分页处理
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ProjectBriefSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ProjectBriefSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def all_projects(self, request):
        """获取所有可见项目（管理员或项目经理可见）"""
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "用户未登录"}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.is_staff or user.role in ['admin', 'project_manager']:
            queryset = Project.objects.all()
            
            # 分页处理
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = ProjectBriefSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = ProjectBriefSerializer(queryset, many=True)
            return Response(serializer.data)
        
        # 对于普通用户，只返回他们参与的项目
        return self.my_projects(request)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """获取项目成员列表"""
        project = self.get_object()
        members = ProjectMember.objects.filter(project=project)
        serializer = ProjectMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """添加项目成员"""
        project = self.get_object()
        
        # 检查权限
        if not HasProjectPermission().has_object_permission(request, self, project, 'can_manage_members'):
            return Response({"error": "您没有权限管理项目成员"}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProjectMemberCreateSerializer(data=request.data, context={'project': project})
        if serializer.is_valid():
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def milestones(self, request, pk=None):
        """获取项目里程碑列表"""
        project = self.get_object()
        milestones = Milestone.objects.filter(project=project)
        serializer = MilestoneSerializer(milestones, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def environments(self, request, pk=None):
        """获取项目环境列表"""
        project = self.get_object()
        environments = Environment.objects.filter(project=project)
        serializer = EnvironmentSerializer(environments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """获取项目文档列表"""
        project = self.get_object()
        documents = ProjectDocument.objects.filter(project=project)
        serializer = ProjectDocumentSerializer(documents, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """获取项目统计信息"""
        project = self.get_object()
        
        # 获取成员统计
        member_stats = ProjectMember.objects.filter(project=project).values('role').annotate(count=Count('id'))
        
        # 获取里程碑统计
        milestone_stats = Milestone.objects.filter(project=project).values('status').annotate(count=Count('id'))
        
        # 获取活动统计
        # 注意：这里需要根据实际项目活动模型进行调整
        activity_stats = {
            'last_30_days': 0,
            'last_7_days': 0
        }
        
        # 获取测试用例统计
        # 注意：这里需要根据实际测试用例模型进行调整
        test_case_stats = {
            'total': project.test_case_count,
            'passed': 0,
            'failed': 0,
            'blocked': 0,
            'not_run': 0
        }
        
        # 获取缺陷统计
        # 注意：这里需要根据实际缺陷模型进行调整
        bug_stats = {
            'total': project.bug_count,
            'open': 0,
            'in_progress': 0,
            'resolved': 0,
            'closed': 0
        }
        
        statistics = {
            'project_id': project.id,
            'project_name': project.name,
            'members': list(member_stats),
            'milestones': list(milestone_stats),
            'activities': activity_stats,
            'test_cases': test_case_stats,
            'bugs': bug_stats
        }
        
        return Response(statistics)

    @action(detail=True, methods=['post'])
    def add_milestone(self, request, pk=None):
        """添加项目里程碑"""
        project = self.get_object()
        
        # Permission check (Use IsProjectManager or a specific permission check)
        # Here, we use IsProjectManager as defined in MilestoneViewSet's original permissions
        if not IsProjectManager().has_object_permission(request, self, project):
             return Response({"error": "您没有权限添加里程碑"}, status=status.HTTP_403_FORBIDDEN)

        serializer = MilestoneSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Manually set the project before saving
            serializer.save(project=project)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectMemberViewSet(viewsets.ModelViewSet):
    """项目成员视图集"""
    # serializer_class = ProjectMemberSerializer # Remove default or keep as fallback
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectMemberCreateSerializer
        return ProjectMemberSerializer # Use standard serializer for other actions

    def get_queryset(self):
        project_id = self.kwargs.get('project_pk')
        if not project_id:
            return ProjectMember.objects.none()
        # Basic permission check: user must be member of the project to view members
        # More granular checks might be needed in get_permissions
        if not ProjectMember.objects.filter(project_id=project_id, user=self.request.user, is_active=True).exists() and not self.request.user.is_staff:
             raise PermissionDenied("您不是该项目成员，无法查看成员列表。")
        return ProjectMember.objects.filter(project_id=project_id)
    
    def get_permissions(self):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id) if project_id else None
        
        if self.action in ['list', 'retrieve']:
            return [IsProjectMember()] # Checks based on project_pk in URL
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
             # Need permission check for managing members within the specific project
             # Example: Check if the user has can_manage_members flag in ProjectMember
             # Or simply restrict to ProjectManager role
             return [IsProjectManager()] # Simplified check
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        project_id = self.kwargs.get('project_pk')
        project = get_object_or_404(Project, pk=project_id)
        # Re-validate to prevent race conditions and ensure user is still valid member
        if ProjectMember.objects.filter(project=project, user=serializer.validated_data['user']).exists():
             raise ValidationError("该用户已经是项目成员")
        serializer.save(project=project)


class MilestoneViewSet(viewsets.ModelViewSet):
    """项目里程碑视图集"""
    serializer_class = MilestoneSerializer
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
            # Check permission
             if not ProjectMember.objects.filter(project_id=project_id, user=self.request.user, is_active=True).exists() and not self.request.user.is_staff:
                 raise PermissionDenied("您不是该项目成员，无法查看里程碑。")
             return Milestone.objects.filter(project_id=project_id)
        if self.request.user.is_staff:
             return Milestone.objects.all()
        return Milestone.objects.none() 
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsProjectManager()] # Assumes IsProjectManager checks based on Milestone's project
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        if not project_id:
             raise ValidationError({"project": "创建里程碑时必须指定项目。"})
        project = get_object_or_404(Project, pk=project_id)
        # Check permission to create milestone in this project
        if not (IsProjectManager().has_object_permission(self.request, self, project) or self.request.user.is_staff):
             raise PermissionDenied("您没有权限在该项目中创建里程碑。")
        serializer.save(project=project)


class EnvironmentViewSet(viewsets.ModelViewSet):
    """
    测试环境视图集
    提供测试环境的 CRUD 操作。
    查询时通常需要提供 'project' 参数来指定项目ID。
    """
    serializer_class = EnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated] # 基础权限
    
    # 筛选和排序
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'is_active'] # 允许按项目和状态筛选
    search_fields = ['name', 'description']     # 按名称和描述搜索
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        根据项目ID过滤环境，或允许管理员查看所有。
        """
        user = self.request.user
        project_id = self.request.query_params.get('project')

        if project_id:
            try:
                project_id = int(project_id)
                # 简单的权限检查：用户必须是该项目的成员才能查看其环境
                if ProjectMember.objects.filter(project_id=project_id, user=user, is_active=True).exists() or user.is_staff:
                    return Environment.objects.filter(project_id=project_id)
                else:
                    raise PermissionDenied("您没有权限访问该项目的环境。")
            except (ValueError, Project.DoesNotExist):
                 return Environment.objects.none() # 无效的项目 ID 则返回空
            
        # 如果没有提供 project_id
        if user.is_staff: # 管理员可以查看所有环境
             return Environment.objects.all()
             
        # 普通用户在不指定项目时，不返回任何环境
        return Environment.objects.none()

    def perform_create(self, serializer):
        """
        创建环境时，确保关联的项目存在且用户有权限。
        """
        project_id = self.request.data.get('project')
        if not project_id:
            # 使用 DRF 的 ValidationError 更标准
            raise ValidationError({"project": ["创建环境时必须指定所属项目。"]})
            
        try:
            project = Project.objects.get(pk=project_id)
            # 权限检查：只有项目经理或管理员才能创建环境 (示例)
            # 使用 IsProjectManager 权限类检查更佳
            if not (IsProjectManager().has_object_permission(self.request, self, project) or self.request.user.is_staff):
                 raise PermissionDenied("您没有权限在该项目中创建环境。")
            # 验证通过后，在 save 时传入 project
            serializer.save(project=project)
        except Project.DoesNotExist:
             raise ValidationError({"project": ["指定的项目不存在。"]})

    def get_permissions(self):
        """根据操作设置更具体的权限"""
        # 对于 list/retrieve, IsAuthenticated 足够，queryset 已经做了过滤
        # 对于 create, 权限检查在 perform_create 中
        if self.action in ['update', 'partial_update', 'destroy']:
            # 需要对象级权限检查
            # 假设 IsProjectManager 能处理对象权限 (检查 obj.project)
            return [permissions.IsAuthenticated(), IsProjectManager()] 
        return [permissions.IsAuthenticated()]


class ProjectDocumentViewSet(viewsets.ModelViewSet):
    """项目文档视图集"""
    serializer_class = ProjectDocumentSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description', 'content']
    filterset_fields = ['doc_type']
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project')
        if project_id:
             # Check permission
             if not ProjectMember.objects.filter(project_id=project_id, user=self.request.user, is_active=True).exists() and not self.request.user.is_staff:
                 raise PermissionDenied("您不是该项目成员，无法查看文档。")
             return ProjectDocument.objects.filter(project_id=project_id)
        if self.request.user.is_staff:
            return ProjectDocument.objects.all()
        return ProjectDocument.objects.none()

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
             return [IsProjectManager()] # Simplified permission
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        project_id = self.request.data.get('project')
        if not project_id:
             raise ValidationError({"project": "创建文档时必须指定项目。"})
        project = get_object_or_404(Project, pk=project_id)
        # Check permission
        if not (IsProjectMember().has_object_permission(self.request, self, project) or self.request.user.is_staff):
             raise PermissionDenied("您没有权限在该项目中创建文档。")
        serializer.save(project=project, created_by=self.request.user)
