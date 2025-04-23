from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限，只允许对象的所有者编辑它。
    读取权限对任何请求都允许，包括 GET, HEAD 或 OPTIONS。
    """

    def has_object_permission(self, request, view, obj):
        # 读取权限允许所有请求 (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写入权限只允许对象的所有者。
        # 假设对象有一个 'owner' 或 'user' 或 'creator' 或 'rated_by' 字段。
        # 对于 UserRating 模型，所有者是 'rated_by' 字段。
        if hasattr(obj, 'rated_by'):
            return obj.rated_by == request.user
        elif hasattr(obj, 'creator'): # Example for other models
            return obj.creator == request.user
        elif hasattr(obj, 'user'): # Example for other models
            return obj.user == request.user
        # 添加其他可能的属主字段检查
        
        # 如果对象没有明确的属主字段，默认不允许写入
        return False 