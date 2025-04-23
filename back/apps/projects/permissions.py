from rest_framework import permissions

class IsProjectMember(permissions.BasePermission):
    """
    确保用户是项目的成员
    """
    message = "您不是该项目的成员，无权访问项目资源"
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 管理员具有全部权限
        if request.user.is_staff or request.user.role == 'admin':
            return True
        
        # 获取项目对象
        if hasattr(obj, 'project'):
            project = obj.project
        else:
            project = obj
            
        # 检查用户是否是项目成员
        return project.members.filter(user=request.user, is_active=True).exists()


class IsProjectManager(permissions.BasePermission):
    """
    确保用户是项目的管理者（项目经理或测试经理）
    """
    message = "只有项目经理或管理员有权执行此操作"
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 管理员具有全部权限
        if request.user.is_staff or request.user.role == 'admin':
            return True
        
        # 获取项目对象
        if hasattr(obj, 'project'):
            project = obj.project
        else:
            project = obj
            
        # 检查用户是否是项目经理或测试经理
        return project.members.filter(
            user=request.user, 
            is_active=True,
            role__in=['project_manager', 'test_manager']
        ).exists()


class HasProjectPermission(permissions.BasePermission):
    """
    检查用户是否具有项目的特定权限
    """
    
    def __init__(self, permission_field=None):
        """
        初始化时指定权限字段，如 'can_manage_members'
        """
        self.permission_field = permission_field
        self.message = f"您没有权限执行此操作，需要 {permission_field} 权限"
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj, permission_field=None):
        # 使用传入的权限字段或初始化时的权限字段
        check_permission = permission_field or self.permission_field
        
        # 管理员具有全部权限
        if request.user.is_staff or request.user.role == 'admin':
            return True
        
        # 获取项目对象
        if hasattr(obj, 'project'):
            project = obj.project
        else:
            project = obj
            
        # 查询用户在该项目中的成员记录
        try:
            member = project.members.get(user=request.user, is_active=True)
            
            # 项目经理有所有权限
            if member.role == 'project_manager':
                return True
                
            # 如果不检查特定权限，则只需是成员即可
            if not check_permission:
                return True
                
            # 检查特定权限
            return getattr(member, check_permission, False)
            
        except Exception:
            return False 