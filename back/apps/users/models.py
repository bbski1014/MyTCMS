# apps/users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class User(AbstractUser):
    """自定义用户模型"""
    phone = models.CharField(max_length=11, unique=True, null=True, blank=True, verbose_name='手机号')
    department = models.CharField(max_length=50, blank=True, verbose_name='部门')
    position = models.CharField(max_length=50, blank=True, verbose_name='职位')
    
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('project_manager', '项目经理'),
        ('tester', '测试人员'),
        ('developer', '开发人员')
    )
    
    name = models.CharField(max_length=50, default='', verbose_name='姓名')
    email = models.EmailField(unique=True, verbose_name='邮箱')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tester', verbose_name='角色')
    
    # 修复权限相关的字段冲突
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='user_groups',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='user_permissions_set',
        related_query_name='user',
    )
    
    class Meta:
        app_label = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        ordering = ['-date_joined']
        
    def __str__(self):
        return self.username or self.name


class UserProfile(models.Model):
    """扩展的用户资料"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile', verbose_name='用户')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    bio = models.TextField(max_length=500, blank=True, verbose_name='个人简介')
    
    # 认证相关
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')
    identity_verified = models.BooleanField(default=False, verbose_name='身份已验证')
    
    # 技能评级
    EXPERIENCE_CHOICES = (
        ('beginner', '初级'),
        ('intermediate', '中级'),
        ('expert', '高级'),
        ('professional', '专家')
    )
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='beginner', verbose_name='经验等级')
    
    # 积分与等级
    points = models.IntegerField(default=0, verbose_name='积分')
    level = models.IntegerField(default=1, verbose_name='等级')
    reputation_score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], verbose_name='信誉评分')
    
    # 社交媒体
    github = models.URLField(blank=True, verbose_name='GitHub')
    linkedin = models.URLField(blank=True, verbose_name='LinkedIn')
    website = models.URLField(blank=True, verbose_name='个人网站')
    
    # 通知设置
    email_notifications = models.BooleanField(default=True, verbose_name='邮件通知')
    
    # 统计数据
    completed_tasks = models.IntegerField(default=0, verbose_name='已完成任务数')
    bugs_found = models.IntegerField(default=0, verbose_name='发现缺陷数')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '用户资料'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.user.username}的资料"


class Skill(models.Model):
    """技能标签"""
    name = models.CharField(max_length=50, unique=True, verbose_name='技能名称')
    category = models.CharField(max_length=50, verbose_name='分类')
    skill_type = models.ForeignKey(
        'SkillType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='skills',
        verbose_name='技能类型'
    )
    description = models.TextField(blank=True, verbose_name='描述')
    
    class Meta:
        verbose_name = '技能'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return self.name


class SkillType(models.Model):
    """技能类型模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name='类型名称')
    category = models.CharField(max_length=50, blank=True, verbose_name='分类')
    description = models.TextField(blank=True, verbose_name='描述')
    icon = models.CharField(max_length=50, blank=True, verbose_name='图标')
    order = models.IntegerField(default=0, verbose_name='排序值')

    class Meta:
        verbose_name = '技能类型'
        verbose_name_plural = verbose_name
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    """用户技能关联"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skills', verbose_name='用户')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, verbose_name='技能')
    proficiency = models.IntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='熟练度')
    years_experience = models.FloatField(default=0, verbose_name='经验年限')
    
    class Meta:
        verbose_name = '用户技能'
        verbose_name_plural = verbose_name
        unique_together = ('user', 'skill')
    
    def __str__(self):
        return f"{self.user.username} - {self.skill.name} ({self.proficiency}级)"


class Device(models.Model):
    """测试设备"""
    DEVICE_TYPE_CHOICES = (
        ('pc', '个人电脑'),
        ('mobile', '移动设备'),
        ('tablet', '平板设备'),
        ('other', '其他设备')
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='devices', verbose_name='用户')
    device_type = models.ForeignKey(
        'DeviceType',
        on_delete=models.PROTECT,
        related_name='devices',
        verbose_name='设备类型'
    )
    device_type_legacy = models.CharField(max_length=20, choices=DEVICE_TYPE_CHOICES, blank=True, null=True, verbose_name='设备类型(旧)')
    name = models.CharField(max_length=100, verbose_name='设备名称')
    os = models.CharField(max_length=50, verbose_name='操作系统')
    os_version = models.CharField(max_length=50, verbose_name='系统版本')
    browser = models.CharField(max_length=50, blank=True, null=True, verbose_name='浏览器')
    browser_version = models.CharField(max_length=50, blank=True, null=True, verbose_name='浏览器版本')
    screen_resolution = models.CharField(max_length=50, blank=True, null=True, verbose_name='屏幕分辨率')
    additional_info = models.TextField(blank=True, null=True, verbose_name='附加信息')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '测试设备'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.name} ({self.os} {self.os_version})"


class UserRating(models.Model):
    """用户评分记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings', verbose_name='用户')
    rated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='given_ratings', verbose_name='评分人')
    
    # 可以关联到项目或任务
    project_id = models.IntegerField(null=True, blank=True, verbose_name='项目ID')
    task_id = models.IntegerField(null=True, blank=True, verbose_name='任务ID')
    
    score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], verbose_name='评分')
    comment = models.TextField(blank=True, verbose_name='评语')
    
    # 评分细分
    quality_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], verbose_name='质量评分')
    efficiency_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], verbose_name='效率评分')
    communication_score = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], verbose_name='沟通评分')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '用户评分'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.user.username}的评分 ({self.score})"


class UserReward(models.Model):
    """用户奖励记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rewards', verbose_name='用户')
    
    # --- Added Fields Start ---
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # 发放者被删除，奖励记录仍保留
        null=True, # 系统自动发放时为空
        blank=True,
        related_name='issued_rewards',
        verbose_name='发放人'
    )
    ISSUANCE_TYPE_CHOICES = (
        ('manual', '手动发放'),
        ('automatic', '自动发放'),
    )
    issuance_type = models.CharField(
        max_length=10,
        choices=ISSUANCE_TYPE_CHOICES,
        default='manual',
        verbose_name='发放类型'
    )
    # --- Added Fields End ---

    # 奖励类型
    REWARD_TYPE_CHOICES = (
        ('point', '积分'),
        ('badge', '徽章'),
        ('level_up', '升级'),
        ('cash', '现金'),
        ('other', '其他')
    )
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES, verbose_name='奖励类型')
    amount = models.IntegerField(default=0, verbose_name='奖励数量')
    description = models.CharField(max_length=200, verbose_name='奖励描述')
    
    # 可以关联到项目或任务
    project_id = models.IntegerField(null=True, blank=True, verbose_name='项目ID')
    task_id = models.IntegerField(null=True, blank=True, verbose_name='任务ID')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        verbose_name = '用户奖励'
        verbose_name_plural = verbose_name
    
    def __str__(self):
        return f"{self.user.username}的{self.get_reward_type_display()} ({self.amount})"


class DeviceType(models.Model):
    """设备类型模型"""
    name = models.CharField(max_length=50, unique=True, verbose_name='类型名称')
    category = models.CharField(max_length=50, verbose_name='分类')
    description = models.TextField(blank=True, verbose_name='描述')
    
    class Meta:
        verbose_name = '设备类型'
        verbose_name_plural = verbose_name
        ordering = ['id']
    
    def __str__(self):
        return self.name


class ExchangeRecord(models.Model):
    """积分兑换记录"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exchange_records', verbose_name='用户')
    item_name = models.CharField(max_length=100, verbose_name='兑换项目名称') # Simplification: store name directly
    # Or use ForeignKey to an ExchangeItem model if items are managed in DB
    # item = models.ForeignKey('ExchangeItem', on_delete=models.PROTECT, verbose_name='兑换项目')
    quantity = models.PositiveIntegerField(default=1, verbose_name='兑换数量')
    points_spent = models.IntegerField(verbose_name='消耗积分')
    
    STATUS_CHOICES = (
        ('pending', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    remark = models.TextField(blank=True, verbose_name='备注')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='兑换时间')

    class Meta:
        verbose_name = '积分兑换记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} 兑换 {self.item_name} ({self.status})"