# Generated by Django 4.2.20 on 2025-04-16 06:03

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        max_length=11,
                        null=True,
                        unique=True,
                        verbose_name="手机号",
                    ),
                ),
                (
                    "department",
                    models.CharField(blank=True, max_length=50, verbose_name="部门"),
                ),
                (
                    "position",
                    models.CharField(blank=True, max_length=50, verbose_name="职位"),
                ),
                (
                    "name",
                    models.CharField(default="", max_length=50, verbose_name="姓名"),
                ),
                (
                    "email",
                    models.EmailField(max_length=254, unique=True, verbose_name="邮箱"),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "管理员"),
                            ("project_manager", "项目经理"),
                            ("tester", "测试人员"),
                            ("developer", "开发人员"),
                        ],
                        default="tester",
                        max_length=20,
                        verbose_name="角色",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_groups",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_permissions_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户",
                "verbose_name_plural": "用户",
                "ordering": ["-date_joined"],
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="技能名称"
                    ),
                ),
                ("category", models.CharField(max_length=50, verbose_name="分类")),
                ("description", models.TextField(blank=True, verbose_name="描述")),
            ],
            options={
                "verbose_name": "技能",
                "verbose_name_plural": "技能",
            },
        ),
        migrations.CreateModel(
            name="UserReward",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "reward_type",
                    models.CharField(
                        choices=[
                            ("point", "积分"),
                            ("badge", "徽章"),
                            ("level_up", "升级"),
                            ("cash", "现金"),
                            ("other", "其他"),
                        ],
                        max_length=20,
                        verbose_name="奖励类型",
                    ),
                ),
                ("amount", models.IntegerField(default=0, verbose_name="奖励数量")),
                (
                    "description",
                    models.CharField(max_length=200, verbose_name="奖励描述"),
                ),
                (
                    "project_id",
                    models.IntegerField(blank=True, null=True, verbose_name="项目ID"),
                ),
                (
                    "task_id",
                    models.IntegerField(blank=True, null=True, verbose_name="任务ID"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rewards",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户奖励",
                "verbose_name_plural": "用户奖励",
            },
        ),
        migrations.CreateModel(
            name="UserRating",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "project_id",
                    models.IntegerField(blank=True, null=True, verbose_name="项目ID"),
                ),
                (
                    "task_id",
                    models.IntegerField(blank=True, null=True, verbose_name="任务ID"),
                ),
                (
                    "score",
                    models.FloatField(
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                        verbose_name="评分",
                    ),
                ),
                ("comment", models.TextField(blank=True, verbose_name="评语")),
                (
                    "quality_score",
                    models.FloatField(
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                        verbose_name="质量评分",
                    ),
                ),
                (
                    "efficiency_score",
                    models.FloatField(
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                        verbose_name="效率评分",
                    ),
                ),
                (
                    "communication_score",
                    models.FloatField(
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                        verbose_name="沟通评分",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "rated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="given_ratings",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="评分人",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ratings",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户评分",
                "verbose_name_plural": "用户评分",
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avatar",
                    models.ImageField(
                        blank=True, null=True, upload_to="avatars/", verbose_name="头像"
                    ),
                ),
                (
                    "bio",
                    models.TextField(
                        blank=True, max_length=500, verbose_name="个人简介"
                    ),
                ),
                (
                    "email_verified",
                    models.BooleanField(default=False, verbose_name="邮箱已验证"),
                ),
                (
                    "identity_verified",
                    models.BooleanField(default=False, verbose_name="身份已验证"),
                ),
                (
                    "experience_level",
                    models.CharField(
                        choices=[
                            ("beginner", "初级"),
                            ("intermediate", "中级"),
                            ("expert", "高级"),
                            ("professional", "专家"),
                        ],
                        default="beginner",
                        max_length=20,
                        verbose_name="经验等级",
                    ),
                ),
                ("points", models.IntegerField(default=0, verbose_name="积分")),
                ("level", models.IntegerField(default=1, verbose_name="等级")),
                (
                    "reputation_score",
                    models.FloatField(
                        default=0.0,
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                        verbose_name="信誉评分",
                    ),
                ),
                ("github", models.URLField(blank=True, verbose_name="GitHub")),
                ("linkedin", models.URLField(blank=True, verbose_name="LinkedIn")),
                ("website", models.URLField(blank=True, verbose_name="个人网站")),
                (
                    "email_notifications",
                    models.BooleanField(default=True, verbose_name="邮件通知"),
                ),
                (
                    "completed_tasks",
                    models.IntegerField(default=0, verbose_name="已完成任务数"),
                ),
                (
                    "bugs_found",
                    models.IntegerField(default=0, verbose_name="发现缺陷数"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户资料",
                "verbose_name_plural": "用户资料",
            },
        ),
        migrations.CreateModel(
            name="Device",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "device_type",
                    models.CharField(
                        choices=[
                            ("pc", "个人电脑"),
                            ("mobile", "移动设备"),
                            ("tablet", "平板设备"),
                            ("other", "其他设备"),
                        ],
                        max_length=20,
                        verbose_name="设备类型",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="设备名称")),
                ("os", models.CharField(max_length=50, verbose_name="操作系统")),
                (
                    "os_version",
                    models.CharField(max_length=50, verbose_name="系统版本"),
                ),
                (
                    "browser",
                    models.CharField(blank=True, max_length=50, verbose_name="浏览器"),
                ),
                (
                    "browser_version",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="浏览器版本"
                    ),
                ),
                (
                    "screen_resolution",
                    models.CharField(
                        blank=True, max_length=50, verbose_name="屏幕分辨率"
                    ),
                ),
                (
                    "additional_info",
                    models.TextField(blank=True, verbose_name="附加信息"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="devices",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "测试设备",
                "verbose_name_plural": "测试设备",
            },
        ),
        migrations.CreateModel(
            name="UserSkill",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "proficiency",
                    models.IntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ],
                        verbose_name="熟练度",
                    ),
                ),
                (
                    "years_experience",
                    models.FloatField(default=0, verbose_name="经验年限"),
                ),
                (
                    "skill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="users.skill",
                        verbose_name="技能",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skills",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "用户技能",
                "verbose_name_plural": "用户技能",
                "unique_together": {("user", "skill")},
            },
        ),
    ]
