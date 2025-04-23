from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# 导入相关应用的模型
# 确保你的 app 路径正确
try:
    from apps.projects.models import Project, Environment
except ImportError:
    # 处理可能的循环导入或应用尚未完全设置的情况
    Project = 'projects.Project'
    Environment = 'projects.Environment'

try:
    from apps.testcases.models import TestCase, TestCaseVersion
except ImportError:
    TestCase = 'testcases.TestCase'
    TestCaseVersion = 'testcases.TestCaseVersion'

# 使用 get_user_model 获取用户模型，更灵活
from django.contrib.auth import get_user_model

User = get_user_model()

class TestPlan(models.Model):
    """测试计划模型"""
    STATUS_CHOICES = (
        ('planning', _('规划中')),
        ('ready', _('准备就绪')),
        ('archived', _('已归档')),
    )

    name = models.CharField(_('计划名称'), max_length=200)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE, # 项目删除，计划也删除
        related_name='test_plans',
        verbose_name=_('所属项目')
    )
    description = models.TextField(_('描述'), blank=True, null=True)
    # Change ManyToManyField name to plan_cases and point to TestCaseVersion
    plan_case_versions = models.ManyToManyField(
        # 'testcases.TestCaseVersion', # Use app_label.ModelName format
        TestCaseVersion, # Direct import should work now if defined earlier in the same app
        related_name='test_plans',
        blank=True,
        verbose_name=_('包含的测试用例版本')
    )
    # --- Keep the old field commented out for reference during migration/code update ---
    # plan_cases = models.ManyToManyField(
    #     TestCase,
    #     related_name='test_plans_old', # Change related_name to avoid conflict
    #     blank=True,
    #     verbose_name=_('包含的测试用例(旧)')
    # )
    # --- End old field reference ---
    creator = models.ForeignKey(
        User,
        related_name='created_test_plans',
        on_delete=models.SET_NULL, # 创建者删除，计划保留
        null=True,
        verbose_name=_('创建人')
    )
    start_date = models.DateField(_('开始日期'), null=True, blank=True)
    end_date = models.DateField(_('结束日期'), null=True, blank=True)
    status = models.CharField(
        _('状态'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning'
    )
    is_active = models.BooleanField(default=True, verbose_name="是否激活") # Added this earlier, good for soft delete/status
    created_at = models.DateTimeField(_('创建时间'), auto_now_add=True)
    updated_at = models.DateTimeField(_('更新时间'), auto_now=True)

    class Meta:
        verbose_name = _('测试计划')
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        # 同一项目下计划名称唯一（如果需要）
        # unique_together = ('project', 'name')

    def __str__(self):
        # 处理 project 可能为 None 的情况 (理论上 on_delete=CASCADE 不会发生)
        project_code = self.project.code if hasattr(self.project, 'code') else 'N/A'
        return f"[{project_code}] {self.name}"

# 后面我们会在这里添加 TestPlanCase, TestRun, TestResult 等模型

# 后面会添加 TestRun, TestResult

class TestRun(models.Model):
    """测试执行轮次"""
    STATUS_CHOICES = [
        ('not_started', '未开始'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('blocked', '已阻塞'),
        ('aborted', '已中止'),
    ]

    name = models.CharField(max_length=200, verbose_name="执行轮次名称")
    test_plan = models.ForeignKey(
        TestPlan,
        on_delete=models.CASCADE, # 测试计划删除，执行轮次也删除
        related_name='test_runs',
        verbose_name="所属测试计划"
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE, # 项目删除，执行轮次也删除
        related_name='test_runs',
        verbose_name="所属项目" # 冗余存储，方便查询
    )
    description = models.TextField(blank=True, null=True, verbose_name="执行描述")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started', db_index=True, verbose_name="状态")
    environment = models.ForeignKey(
        Environment,
        on_delete=models.SET_NULL, # 环境删除，执行轮次保留
        null=True,
        blank=True,
        related_name='test_runs',
        verbose_name="测试环境"
    )
    assignee = models.ForeignKey(
        User,
        related_name='assigned_test_runs',
        on_delete=models.SET_NULL, # 执行人删除，执行轮次保留
        null=True,
        blank=True,
        verbose_name="负责人/执行人"
    )
    # --- Remove redundant M2M field, relationship is now defined by TestResult --- 
    # testcases = models.ManyToManyField(
    #     TestCase, # This should probably point to TestCaseVersion if kept
    #     related_name='test_runs_m2m', # Adjusted related_name to avoid clash if TestResult isn't through model
    #     blank=True, # 允许创建空的 TestRun 后再添加用例
    #     verbose_name="包含的测试用例",
    #     through='TestResult', # Explicitly state the through model for M2M
    #     through_fields=('test_run', 'testcase'), # Specify relationship fields
    # )
    # --- End Removal --- 
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="实际开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="实际结束时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "测试执行轮次"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        project_code = self.project.code if hasattr(self.project, 'code') else 'N/A'
        plan_name = self.test_plan.name if hasattr(self.test_plan, 'name') else 'N/A'
        return f"[{project_code}] {self.name} ({plan_name})"

    # 可以添加计算属性获取进度等
    # @property
    # def progress(self): ...
    # @property
    # def pass_rate(self): ...

class TestResult(models.Model):
    """单个测试用例的执行结果 (作为 TestRun 和 TestCase 的 M2M 'through' 模型)"""
    STATUS_CHOICES = [
        ('untested', '未测试'),
        ('passed', '通过'),
        ('failed', '失败'),
        ('skipped', '跳过'),
        ('blocked', '阻塞'),
    ]

    test_run = models.ForeignKey(
        TestRun,
        on_delete=models.CASCADE, # 执行轮次删除，结果也删除
        related_name='results', # related_name to link from TestRun
        verbose_name="所属执行轮次"
    )
    # Modify the ForeignKey to point to TestCaseVersion
    testcase_version = models.ForeignKey(
        # 'testcases.TestCaseVersion', # Use app_label.ModelName format
        TestCaseVersion, # Direct import should work now
        on_delete=models.CASCADE, # Or SET_NULL if a version deletion shouldn't delete results
        related_name='results',
        verbose_name="测试用例版本",
        null=True # Temporarily allow null to satisfy makemigrations
    )
    # --- Keep the old field commented out for reference --- 
    # testcase = models.ForeignKey(
    #     TestCase,
    #     on_delete=models.CASCADE, # 用例删除，结果也删除 (可改为 SET_NULL 保持历史)
    #     related_name='results_old', # Change related_name
    #     verbose_name="测试用例(旧)"
    # )
    # --- End old field reference ---
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='untested', db_index=True, verbose_name="执行状态")
    executor = models.ForeignKey(
        User,
        related_name='executed_results',
        on_delete=models.SET_NULL, # 执行人删除，结果保留
        null=True,
        blank=True, # 允许匿名执行或系统执行
        verbose_name="执行人"
    )
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name="执行完成时间") # 记录完成时间
    duration = models.DurationField(null=True, blank=True, verbose_name="执行耗时")
    comments = models.TextField(blank=True, null=True, verbose_name="实际结果/备注")
    # 关联缺陷，可以存 JIRA Key 或内部系统 ID
    bug_id = models.CharField(max_length=50, blank=True, null=True, db_index=True, verbose_name="关联缺陷ID")
    # 可以添加附件字段，如 FileField 或链接到对象存储

    class Meta:
        verbose_name = "测试结果"
        verbose_name_plural = verbose_name
        # 一个用例在一个执行轮次中应该只有一个最终结果记录
        unique_together = ('test_run', 'testcase_version') # Restore the constraint
        ordering = ['-executed_at'] # 按执行时间倒序

    def __str__(self):
        case_title = self.testcase_version.title if hasattr(self.testcase_version, 'title') else f'ID:{self.testcase_version_id}'
        run_name = self.test_run.name if hasattr(self.test_run, 'name') else f'ID:{self.test_run_id}'
        return f"Run: {run_name} - Case: {case_title} - {self.get_status_display()}"
