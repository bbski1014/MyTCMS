from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from pgvector.django import VectorField # 导入 VectorField

# Ensure the Project model path is correct based on your app structure
# If your project app is named differently, adjust 'projects.Project' accordingly.
# from apps.projects.models import Project # Example if Project is in apps.projects

class Module(models.Model):
    """测试用例模块/目录"""
    name = models.CharField(max_length=100, verbose_name="模块名称")
    # Ensure the ForeignKey points to the correct Project model location
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='modules', verbose_name="所属项目") 
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children', verbose_name="父模块")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "测试模块"
        verbose_name_plural = verbose_name
        unique_together = ('project', 'name', 'parent') # 同一项目下，同一父模块下的名称唯一
        ordering = ['name']

    def __str__(self):
        # Handle potential None project if needed, though CASCADE should prevent it
        project_name = self.project.name if self.project else "未分配项目"
        return f"{project_name} - {self.name}"

class Tag(models.Model):
    """标签"""
    name = models.CharField(max_length=50, unique=True, verbose_name="标签名")
    # Consider project-specific tags if needed:
    # project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='tags', null=True, blank=True, verbose_name="所属项目")

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name

class TestCase(models.Model):
    """测试用例实体 (元数据)"""
    # --- 将 Choices 定义移到前面 ---
    PRIORITY_CHOICES = [
        (1, 'P1 - Blocker'),
        (2, 'P2 - Critical'),
        (3, 'P3 - Major'),
        (4, 'P4 - Minor'),
        (5, 'P5 - Trivial'),
    ]
    TYPE_CHOICES = [
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('security', '安全测试'),
        ('ui', 'UI测试'),
        ('api', '接口测试'),
        ('compatibility', '兼容性测试'),
        ('other', '其他'),
    ]
    METHOD_CHOICES = [
        ('manual', '手动'),
        ('automated', '自动'),
    ]
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('ready', '待评审'),
        ('reviewing', '评审中'),
        ('approved', '已批准'),
        ('obsolete', '废弃'),
    ]
    # --- 结束 Choices ---

    # --- 保留的元数据字段 ---
    title = models.CharField(max_length=255, verbose_name="用例标题") # 作为主要标识符
    module = models.ForeignKey(Module, on_delete=models.SET_NULL, null=True, blank=True, related_name='testcases', verbose_name="所属模块")
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='testcases', verbose_name="所属项目")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="状态") # 用例本身的生命周期状态
    tags = models.ManyToManyField(Tag, blank=True, related_name='testcases', verbose_name="标签")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_testcases', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="创建人")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='updated_testcases', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="最后修改人")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    # --- 结束保留字段 ---
    
    # --- 移除的内容字段 (移动到 TestCaseVersion) ---
    # preconditions = models.TextField(blank=True, null=True, verbose_name="前置条件")
    # priority = models.PositiveSmallIntegerField(choices=TestCase.PRIORITY_CHOICES, default=3, verbose_name="优先级")
    # case_type = models.CharField(max_length=50, choices=TestCase.TYPE_CHOICES, default='functional', verbose_name="用例类型")
    # method = models.CharField(max_length=20, choices=TestCase.METHOD_CHOICES, default='manual', verbose_name="执行方式")
    # --- 结束移除字段 ---
    
    # --- 添加指向活动版本的链接 ---
    active_version = models.ForeignKey(
        'TestCaseVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+', # 不需要从 Version 反向查找 active_in_cases
        verbose_name=_('当前活动版本')
    )
    # --- 结束添加链接 ---

    # --- Choices 已移到前面 ---
    # PRIORITY_CHOICES = [...]
    # TYPE_CHOICES = [...]
    # METHOD_CHOICES = [...]
    # STATUS_CHOICES = [...]
    # --- 结束 Choices ---

    class Meta:
        verbose_name = "测试用例"
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        project_name = self.project.name if self.project else "未分配项目"
        return f"[{project_name}] {self.title}"

# --- 移除 TestStep 模型 --- 
# class TestStep(models.Model):
#     """测试步骤"""
#     testcase = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='steps', verbose_name="所属用例")
#     step_number = models.PositiveIntegerField(verbose_name="步骤编号")
#     action = models.TextField(verbose_name="操作步骤")
#     expected_result = models.TextField(verbose_name="预期结果")
#     # actual_result and status should be part of execution records, not the step itself
# 
#     class Meta:
#         verbose_name = "测试步骤"
#         verbose_name_plural = verbose_name
#         ordering = ['step_number']
#         unique_together = ('testcase', 'step_number') # Step numbers unique per test case
# 
#     def __str__(self):
#         return f"{self.testcase.title} - Step {self.step_number}"
# --- 结束移除 TestStep 模型 ---

from django.conf import settings # For User model

class TestCaseVersion(models.Model):
    """
    存储测试用例特定版本内容的快照。
    """
    test_case = models.ForeignKey(
        'TestCase', # Use string reference to avoid import issues if defined later
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name=_('原始测试用例')
    )
    version_number = models.PositiveIntegerField(verbose_name=_('版本号')) # Simple incrementing number per TestCase
    # Or: version_name = models.CharField(max_length=100, verbose_name=_('版本名称/标签')) # More descriptive

    # --- Core TestCase Content Snapshot ---
    title = models.CharField(_('用例标题'), max_length=255)
    precondition = models.TextField(_('前置条件'), blank=True, null=True)
    # Assuming priority, type, method are stored as CharFields based on previous context
    priority = models.CharField(_('优先级'), max_length=20, blank=True)
    case_type = models.CharField(_('用例类型'), max_length=50, blank=True)
    method = models.CharField(_('测试方法'), max_length=50, blank=True)
    # --- End Core Content ---

    # --- Store Steps (Simplified) ---
    # Option 1: JSONField (Requires PostgreSQL or modern MySQL/SQLite)
    steps_data = models.JSONField(_('步骤数据 (JSON)'), default=list, blank=True)
    # Example structure for steps_data:
    # [
    #   {"step": 1, "action": "Step 1 Action", "expected": "Step 1 Expected"},
    #   {"step": 2, "action": "Step 2 Action", "expected": "Step 2 Expected"},
    # ]
    # Option 2: TextField (Simpler, less structured)
    # steps_text = models.TextField(_('步骤文本'), blank=True)
    # (Would need a consistent format, e.g., Markdown, for parsing/display)
    # Let's start with JSONField as it's more structured.
    # --- End Store Steps ---

    # --- 新增 Embedding 字段 ---
    embedding = VectorField(
        dimensions=768,  # 必须与 paraphrase-multilingual-mpnet-base-v2 模型输出维度一致
        null=True,       # 允许为空，因为生成可能需要时间或失败
        blank=True,
        verbose_name="语义向量"
    )
    embedding_model_version = models.CharField(
        max_length=100, # 足够存储模型名称和版本号
        null=True,
        blank=True,
        verbose_name="嵌入模型版本" # 记录生成此向量的模型信息
    )
    # --- 结束新增字段 ---

    # --- Version Metadata ---
    change_description = models.TextField(_('版本变更说明'), blank=True) # Reason for this version
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_testcase_versions',
        null=True,
        blank=True, # Could be system generated or initial import
        verbose_name=_('版本创建者')
    )
    created_at = models.DateTimeField(_('版本创建时间'), auto_now_add=True)
    is_active = models.BooleanField(default=False, db_index=True, verbose_name=_('是否为活动版本')) # Only one active version per TestCase recommended

    class Meta:
        verbose_name = _('测试用例版本')
        verbose_name_plural = verbose_name
        # Ensure unique version per test case
        unique_together = ('test_case', 'version_number')
        ordering = ['test_case', '-version_number'] # Show latest version first for a case

    def __str__(self):
        return f"{self.test_case.title} - v{self.version_number}"


class TestCaseStep(models.Model):
    """测试用例步骤"""
    version = models.ForeignKey(
        'TestCaseVersion',
        on_delete=models.CASCADE,
        related_name='steps',
        null=True,  # Allow null temporarily for migration
        blank=True, # Allow blank temporarily for migration
        verbose_name=_('所属版本')
    )
    step_number = models.PositiveIntegerField(verbose_name='步骤编号')
    action = models.TextField(verbose_name='操作步骤')
    expected_result = models.TextField(blank=True, verbose_name='预期结果')
    # notes = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        verbose_name = _('测试步骤')
        verbose_name_plural = verbose_name
        ordering = ['version', 'step_number']
        unique_together = ('version', 'step_number')

    def __str__(self):
        # Handle None version temporarily
        version_str = str(self.version) if self.version else "[No Version]"
        return f"{version_str} - Step {self.step_number}"
