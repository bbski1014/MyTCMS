# back/apps/testcases/management/commands/generate_test_data.py

import random
import time
import datetime
import json # 导入 json 库
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError # Import IntegrityError
# 明确导入 Project 和 Module 模型
try:
    from apps.projects.models import Project
    from apps.testcases.models import Module # Module 在 testcases 应用下
except ImportError:
    raise CommandError("无法导入 Project 或 Module 模型。请确保 apps.projects 和 apps.testcases 应用已正确配置。")

from apps.testcases.models import TestCase, TestCaseVersion

User = get_user_model()

# --- 文本生成模板 (用于制造语义相似数据) ---
LOGIN_TITLES = [
    "用户登录功能验证", "测试用户登录", "验证有效用户登录", "Login Functionality Test",
    "User Authentication Check", "系统入口：用户登录"
]
LOGIN_PRECONDITIONS = [
    "用户已注册", "浏览器已打开登录页面", "网络连接正常", "测试环境可用",
    "User account exists", "Login page is accessible"
]
LOGIN_STEPS = [
    [{"step": 1, "action": "输入有效用户名", "expected_result": "用户名正常显示"}, {"step": 2, "action": "输入正确密码", "expected_result": "密码以掩码显示"}, {"step": 3, "action": "点击登录按钮", "expected_result": "成功登录并跳转到主页"}],
    [{"step": 1, "action": "输入用户名", "expected_result": "字段接受输入"}, {"step": 2, "action": "输入密码", "expected_result": "字段接受输入"}, {"step": 3, "action": "点击'登录'", "expected_result": "验证通过，显示欢迎信息"}],
    [{"step": 1, "action": "Navigate to login page", "expected_result": "Login form displayed"}, {"step": 2, "action": "Enter valid username", "expected_result": "Username field populated"}, {"step": 3, "action": "Enter valid password", "expected_result": "Password field populated"}, {"step": 4, "action": "Click Submit", "expected_result": "User logged in successfully, redirected to dashboard"}],
]

SEARCH_TITLES = [
    "搜索功能测试", "验证搜索结果准确性", "商品搜索功能", "Test Search Functionality",
    "Verify Search Results", "全局搜索验证"
]
SEARCH_PRECONDITIONS = [
    "索引已建立", "数据库包含测试商品", "用户已登录（可选）", "搜索框可见",
    "Search index is up-to-date", "Test products exist in DB"
]
SEARCH_STEPS = [
    [{"step": 1, "action": "在搜索框输入'测试商品A'", "expected_result": "下拉建议显示相关项"}, {"step": 2, "action": "点击搜索按钮", "expected_result": "搜索结果页面显示'测试商品A'"}, {"step": 3, "action": "检查结果排序", "expected_result": "相关性排序正确"}],
    [{"step": 1, "action": "输入查询关键字'测试'", "expected_result": "Input field updated"}, {"step": 2, "action": "提交搜索", "expected_result": "Results page loads"}, {"step": 3, "action": "验证第一条结果包含'测试'", "expected_result": "First result is relevant"}],
]

SCENARIOS = [
    {"titles": LOGIN_TITLES, "preconditions": LOGIN_PRECONDITIONS, "steps": LOGIN_STEPS},
    {"titles": SEARCH_TITLES, "preconditions": SEARCH_PRECONDITIONS, "steps": SEARCH_STEPS},
    # 可以添加更多场景...
]
# --- End Text Templates ---

# +++ 添加常用模块名称列表 +++
COMMON_MODULE_NAMES = [
    "用户管理", "权限管理", "登录与注册", "搜索功能", "订单处理",
    "支付模块", "商品管理", "基础设置", "数据报表", "API 测试",
    "UI 自动化", "性能基准"
]
# +++ 结束模块名称列表 +++

class Command(BaseCommand):
    help = '批量生成测试用例和版本数据（包括模块），用于测试去重功能。需要数据库中预先存在用户和项目。'

    def add_arguments(self, parser):
        parser.add_argument(
            'num_cases',
            type=int,
            help='要创建的 TestCase 数量。',
        )
        parser.add_argument(
            'versions_per_case',
            type=int,
            default=3,
            help='为每个 TestCase 创建的版本数量 (建议 >= 2 以产生对比)。',
        )
        parser.add_argument(
            '--project-id',
            type=int,
            help='(可选) 指定要将用例创建在哪个项目下。如果省略，则随机选择现有项目。',
        )

    @transaction.atomic # 使用事务确保数据一致性
    def handle(self, *args, **options):
        num_cases = options['num_cases']
        versions_per_case = options['versions_per_case']
        project_id_arg = options['project_id']

        if num_cases <= 0 or versions_per_case <= 0:
            raise CommandError("TestCase 数量和每个用例的版本数量必须大于 0。")

        # --- 1. 查询有效的依赖 ID (用户) ---
        user_ids = list(User.objects.values_list('id', flat=True))
        if not user_ids:
            raise CommandError("数据库中没有用户。请先通过 'python manage.py createsuperuser' 创建用户。")
        first_user_id = user_ids[0] # 获取第一个用户 ID 用于创建默认项目

        # --- 1a. 查询或创建项目 ID ---
        if project_id_arg:
            # 用户指定了项目 ID
            if not Project.objects.filter(pk=project_id_arg).exists():
                raise CommandError(f"找不到指定的项目 ID: {project_id_arg}。")
            project_ids_to_process = [project_id_arg]
            self.stdout.write(f"将在指定的项目 ID {project_id_arg} 中创建数据...")
        else:
            # 用户未指定项目 ID，检查是否存在项目
            existing_project_ids = list(Project.objects.values_list('id', flat=True))
            if not existing_project_ids:
                # 没有项目，自动创建一个默认项目
                self.stdout.write(self.style.WARNING("数据库中没有项目，将自动创建一个默认项目..."))
                try:
                    # 使用正确的 'creator_id' 字段
                    default_project = Project.objects.create(
                        name="默认测试项目",
                        # 使用 creator_id 关联第一个用户
                        creator_id=first_user_id,
                        # 需要提供 Project 模型中其他必填字段的默认值
                        # 假设 start_date 是必填的
                        start_date=datetime.date.today(), # 使用当前日期作为开始日期
                        # 假设 code 是必填且唯一的
                        code=f"DEFAULT_{int(time.time())}", # 生成一个基于时间的唯一代号
                        # 根据你的 Project 模型，可能还需要其他必填字段
                    )
                    project_ids_to_process = [default_project.id]
                    self.stdout.write(self.style.SUCCESS(f"已创建默认项目 ID: {default_project.id}。"))
                except Exception as e:
                     raise CommandError(f"自动创建默认项目时出错: {e}。请检查 Project 模型的必填字段。")
            else:
                # 已有项目，使用所有现有项目
                project_ids_to_process = existing_project_ids
                self.stdout.write(f"将在 {len(project_ids_to_process)} 个现有项目中随机创建数据...")

        # +++ 1b. 为每个项目批量生成常用模块 (忽略冲突) +++
        self.stdout.write("正在为项目创建/确保常用模块存在...")
        modules_created_count = 0
        for project_id in project_ids_to_process:
            modules_to_create_for_project = []
            for module_name in COMMON_MODULE_NAMES:
                modules_to_create_for_project.append(
                    Module(name=module_name, project_id=project_id, parent=None)
                )
            try:
                 # 使用 bulk_create 并忽略可能的唯一性冲突 (name+project+parent)
                 # 这意味着如果模块已存在，则不会重复创建
                created_modules = Module.objects.bulk_create(modules_to_create_for_project, ignore_conflicts=True)
                modules_created_count += len(created_modules) # bulk_create 返回实际创建的对象列表
            except Exception as e:
                # 捕捉可能的其他数据库错误
                 self.stderr.write(self.style.ERROR(f"为项目 {project_id} 创建模块时出错: {e}"))
                 # 可以选择是继续还是停止
                 # raise CommandError("创建模块时发生错误。") # 如果希望停止
        self.stdout.write(f"模块处理完成，共创建了 {modules_created_count} 个新模块 (已存在的会被忽略)。")
        # +++ 结束生成模块 +++


        # --- 1c. 重新查询有效的模块 ID ---
        # 注意: 这里不直接使用 module_ids 变量存储所有模块 ID，而是在生成 TestCase 时
        # 根据选定的 project_id 动态查询该项目下的模块。

        self.stdout.write(f"准备生成 {num_cases} 个 TestCase，每个包含 {versions_per_case} 个版本...")
        start_time = time.time()

        # --- 2. 批量生成 TestCase ---
        test_cases_to_create = []
        for i in range(num_cases):
            # 现在从 project_ids_to_process 中选择项目
            selected_project_id = random.choice(project_ids_to_process)

            # --- 更新模块选择逻辑 ---
            # 为选定的项目获取其模块 ID
            current_project_module_ids = list(Module.objects.filter(project_id=selected_project_id).values_list('id', flat=True))
            # 从该项目的模块中随机选择，或设为 None
            selected_module_id = random.choice(current_project_module_ids + [None]) if current_project_module_ids else None
            # --- 结束模块选择逻辑更新 ---

            scenario = random.choice(SCENARIOS)
            base_title = random.choice(scenario['titles'])

            test_case = TestCase(
                title=f"{base_title} - Base #{i+1}",
                project_id=selected_project_id,
                module_id=selected_module_id, # 使用上面更新的选择逻辑
                status=random.choice([s[0] for s in TestCase.STATUS_CHOICES if s[0] != 'obsolete']), # 避免直接创建废弃的
                created_by_id=random.choice(user_ids),
                updated_by_id=random.choice(user_ids),
            )
            test_cases_to_create.append(test_case)

        created_test_cases = TestCase.objects.bulk_create(test_cases_to_create)
        self.stdout.write(f"成功创建 {len(created_test_cases)} 个 TestCase。")

        # --- 3. 批量生成 TestCaseVersion ---
        test_case_versions_to_create = []
        for test_case in created_test_cases:
            scenario = random.choice(SCENARIOS)
            for j in range(versions_per_case):
                version_number = j + 1
                title_variation = f"{random.choice(scenario['titles'])} (v{version_number})"
                precondition_variation = random.choice(scenario['preconditions'])
                steps_variation_raw = random.choice(scenario['steps']) # 原始模板数据

                # +++ 显式处理 steps_data +++
                try:
                    # 先 dump 成标准 JSON 字符串 (ensure_ascii=False 保留中文)
                    steps_json_str = json.dumps(steps_variation_raw, ensure_ascii=False)
                    # 再 load 回 Python 对象，确保结构和转义规范
                    steps_variation_safe = json.loads(steps_json_str)
                except (TypeError, json.JSONDecodeError) as e:
                    self.stderr.write(self.style.ERROR(f"处理步骤数据时出错 (TC: {test_case.id}, V: {version_number}): {e}"))
                    steps_variation_safe = [] # 如果处理失败，则使用空列表
                # +++ 结束处理 +++

                version = TestCaseVersion(
                    test_case=test_case,
                    version_number=version_number,
                    title=title_variation,
                    precondition=precondition_variation,
                    steps_data=steps_variation_safe, # <-- 使用处理过的安全数据
                    priority=str(random.choice([p[0] for p in TestCase.PRIORITY_CHOICES])),
                    case_type=random.choice([t[0] for t in TestCase.TYPE_CHOICES]),
                    method=random.choice([m[0] for m in TestCase.METHOD_CHOICES]),
                    change_description=f"自动生成的版本 {version_number}",
                    creator_id=random.choice(user_ids),
                )
                test_case_versions_to_create.append(version)

        created_versions = TestCaseVersion.objects.bulk_create(test_case_versions_to_create)
        self.stdout.write(f"成功创建 {len(created_versions)} 个 TestCaseVersion。")

        end_time = time.time()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(
            f"测试数据生成完成。总耗时: {duration:.2f} 秒。"
        ))
        self.stdout.write(self.style.NOTICE(
            "请运行 'python manage.py backfill_embeddings' 来为新生成的版本创建 embedding。"
        ))
        self.stdout.write(self.style.NOTICE(
            "然后运行 'python manage.py find_all_duplicates' 来查找重复对。"
        )) 