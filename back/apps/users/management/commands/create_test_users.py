from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError

User = get_user_model()

# 调整 TEST_USERS 结构，包含 role 字段的值
TEST_USERS = [
    {'username': 'manager_alice', 'role': 'admin', 'role_hint': 'Manager/Admin'},
    {'username': 'lead_bob', 'role': 'project_manager', 'role_hint': 'Project Manager'}, # 假设项目经理是组长
    {'username': 'tester_charlie', 'role': 'tester', 'role_hint': 'Tester'},
    # 注意：没有 'viewer' 角色，我们可以创建一个 developer 或另一个 tester
    # 或者你可以考虑在 User 模型中添加 'viewer' 角色
    {'username': 'dev_david', 'role': 'developer', 'role_hint': 'Developer'},
]
COMMON_PASSWORD = '20021231'

class Command(BaseCommand):
    help = f'创建一组具有预设密码 ({COMMON_PASSWORD}) 和角色的测试用户。'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("开始创建测试用户...")
        created_count = 0
        skipped_count = 0

        for user_data in TEST_USERS:
            username = user_data['username']
            role = user_data['role'] # 获取要设置的角色

            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"用户 '{username}' 已存在，跳过创建。"))
                skipped_count += 1
                continue

            try:
                # 使用 create_user 创建用户，然后设置 role 并保存
                user = User.objects.create_user(username=username, password=COMMON_PASSWORD)
                user.role = role # 直接设置 role 字段
                # 可以设置其他字段，例如姓名
                user.name = username.replace('_', ' ').title() # 简单的姓名生成
                user.email = f"{username}@example.com" # 示例邮箱
                user.save() # 保存 role 和其他字段

                self.stdout.write(self.style.SUCCESS(f"成功创建用户 '{username}' (角色: {role})。"))
                created_count += 1
            except IntegrityError as e:
                 # 检查是否是邮箱冲突
                if 'email' in str(e).lower():
                     self.stderr.write(self.style.ERROR(f"创建用户 '{username}' 时邮箱冲突，请确保 @example.com 邮箱未被使用。"))
                else:
                     self.stderr.write(self.style.ERROR(f"创建用户 '{username}' 时发生 IntegrityError，可能已存在或邮箱冲突。" + str(e)))
                skipped_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"创建用户 '{username}' 时发生意外错误: {e}"))

        self.stdout.write("\n测试用户创建完成。")
        self.stdout.write(f"成功创建: {created_count} 个")
        self.stdout.write(f"已存在/错误跳过: {skipped_count} 个")
        if created_count > 0:
             self.stdout.write(f"所有新创建用户的密码均为: {COMMON_PASSWORD}") 