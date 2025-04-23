from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class ProjectTag(models.Model):
    """项目标签模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name="标签名称")
    color = models.CharField(max_length=20, default="#409EFF", verbose_name="标签颜色")
    description = models.CharField(max_length=200, blank=True, verbose_name="标签描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        verbose_name = "项目标签"
        verbose_name_plural = verbose_name
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Project(models.Model):
    """项目基本信息模型"""
    STATUS_CHOICES = (
        ('planning', '规划中'),
        ('in_progress', '进行中'),
        ('suspended', '已暂停'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )
    
    PRIORITY_CHOICES = (
        (1, '低'),
        (2, '中'),
        (3, '高'),
        (4, '紧急'),
    )
    
    name = models.CharField(max_length=100, verbose_name="项目名称")
    code = models.CharField(max_length=20, unique=True, verbose_name="项目代号")
    description = models.TextField(blank=True, verbose_name="项目描述")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name="项目状态")
    priority = models.SmallIntegerField(choices=PRIORITY_CHOICES, default=2, verbose_name="优先级")
    
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(null=True, blank=True, verbose_name="结束日期")
    
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects', verbose_name="创建者")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects', verbose_name="项目经理")
    
    tags = models.ManyToManyField(ProjectTag, blank=True, related_name='projects', verbose_name="项目标签")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 项目相关统计数据
    test_case_count = models.IntegerField(default=0, verbose_name="测试用例数量")
    bug_count = models.IntegerField(default=0, verbose_name="缺陷数量")
    
    class Meta:
        verbose_name = "项目"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class ProjectMember(models.Model):
    """项目成员模型"""
    ROLE_CHOICES = (
        ('project_manager', '项目经理'),
        ('test_manager', '测试经理'),
        ('tester', '测试人员'),
        ('developer', '开发人员'),
        ('observer', '观察者'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members', verbose_name="项目")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships', verbose_name="用户")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name="角色")
    
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")
    
    # 可选：为每个成员分配特定的权限
    can_manage_members = models.BooleanField(default=False, verbose_name="可管理成员")
    can_manage_test_cases = models.BooleanField(default=False, verbose_name="可管理测试用例")
    can_manage_executions = models.BooleanField(default=False, verbose_name="可管理测试执行")
    
    class Meta:
        verbose_name = "项目成员"
        verbose_name_plural = verbose_name
        unique_together = ['project', 'user']  # 一个用户在一个项目中只能有一个角色
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()} ({self.project.name})"

class Milestone(models.Model):
    """项目里程碑模型"""
    STATUS_CHOICES = (
        ('planned', '计划中'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('delayed', '已延期'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='milestones', verbose_name="项目")
    name = models.CharField(max_length=100, verbose_name="里程碑名称")
    description = models.TextField(blank=True, verbose_name="描述")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned', verbose_name="状态")
    
    start_date = models.DateField(verbose_name="开始日期")
    due_date = models.DateField(verbose_name="截止日期")
    completed_date = models.DateField(null=True, blank=True, verbose_name="完成日期")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "里程碑"
        verbose_name_plural = verbose_name
        ordering = ['due_date']
    
    def __str__(self):
        return f"{self.name} ({self.project.name})"

class Environment(models.Model):
    """测试环境模型"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments', verbose_name="项目")
    name = models.CharField(max_length=100, verbose_name="环境名称")
    description = models.TextField(blank=True, verbose_name="环境描述")
    
    # 环境配置，如服务器地址、数据库配置等
    server_url = models.URLField(blank=True, verbose_name="服务器地址")
    api_base_url = models.URLField(blank=True, verbose_name="API基础地址")
    database_config = models.JSONField(blank=True, null=True, verbose_name="数据库配置")
    env_variables = models.JSONField(blank=True, null=True, verbose_name="环境变量")
    
    is_active = models.BooleanField(default=True, verbose_name="是否可用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "测试环境"
        verbose_name_plural = verbose_name
        unique_together = ['project', 'name']  # 在同一项目中环境名称唯一
    
    def __str__(self):
        return f"{self.name} ({self.project.name})"

class ProjectDocument(models.Model):
    """项目文档模型"""
    DOCUMENT_TYPES = (
        ('requirement', '需求文档'),
        ('design', '设计文档'),
        ('test_plan', '测试计划'),
        ('api_doc', 'API文档'),
        ('user_manual', '用户手册'),
        ('other', '其他'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents', verbose_name="项目")
    title = models.CharField(max_length=200, verbose_name="文档标题")
    doc_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, verbose_name="文档类型")
    description = models.TextField(blank=True, verbose_name="文档描述")
    
    file = models.FileField(upload_to='project_documents/%Y/%m/', blank=True, null=True, verbose_name="文档文件")
    url = models.URLField(blank=True, verbose_name="文档链接")
    content = models.TextField(blank=True, verbose_name="文档内容")
    
    version = models.CharField(max_length=50, blank=True, verbose_name="文档版本")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents', verbose_name="上传者")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "项目文档"
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_doc_type_display()})"
