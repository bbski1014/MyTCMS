# back/apps/analysis/views.py
from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import PotentialDuplicatePair
from .serializers import PotentialDuplicatePairSerializer

class PotentialDuplicatePairViewSet(viewsets.ModelViewSet):
    """
    API endpoint allowing potential duplicate pairs to be viewed or edited.
    """
    queryset = PotentialDuplicatePair.objects.select_related('version_a', 'version_b').all()
    serializer_class = PotentialDuplicatePairSerializer
    # 设置权限，例如只允许认证用户访问
    permission_classes = [permissions.IsAuthenticated]
    # 添加过滤和排序功能
    filter_backends = [
        DjangoFilterBackend,        # 支持基于字段的过滤
        filters.OrderingFilter,     # 支持排序
        # filters.SearchFilter      # 如果需要文本搜索，可以添加
    ]
    # 定义可用于过滤的字段
    filterset_fields = [
        'status',
        'version_a__test_case__project', # 按项目过滤 (通过 version_a 关联)
        # 可以添加更多过滤字段，例如 'version_a__id', 'version_b__id'
        ]
    # 定义可用于排序的字段
    ordering_fields = ['similarity_score', 'created_at', 'status']
    # 默认排序
    ordering = ['-similarity_score']

    # 如果只允许读取和修改状态，可以限制 HTTP 方法
    # http_method_names = ['get', 'patch', 'head', 'options']

    # 如果需要对 version_a 或 version_b 的项目进行过滤，
    # 可能需要更复杂的过滤逻辑或自定义 FilterSet。
    # 这里示例了按 version_a 关联的项目过滤。

    # 如果允许更新 status，可以在 serializer 中去掉 status 的 read_only=True
    # 并在这里可能需要重写 perform_update 来记录操作者等。

# Create your views here. 