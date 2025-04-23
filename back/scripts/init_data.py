# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model
from users.models import Skill, DeviceType

User = get_user_model()

# 创建管理员用户
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
        name='管理员',
        role='admin'
    )
    print('已创建管理员用户: admin (密码: admin123)')

# 创建技能类型
skill_types = [
    {'name': 'Web测试', 'category': '功能测试', 'description': '网页功能和界面测试'},
    {'name': '移动应用测试', 'category': '功能测试', 'description': '移动应用兼容性和功能测试'},
    {'name': 'API测试', 'category': '功能测试', 'description': '接口功能和性能测试'},
    {'name': '自动化测试', 'category': '技术测试', 'description': '使用工具进行自动化测试'},
    {'name': '安全测试', 'category': '专项测试', 'description': '安全漏洞和渗透测试'},
    {'name': '性能测试', 'category': '专项测试', 'description': '系统性能和负载测试'}
]

for skill_data in skill_types:
    skill, created = Skill.objects.get_or_create(
        name=skill_data['name'],
        defaults=skill_data
    )
    if created:
        print(f'已添加技能类型: {skill_data["name"]}')

# 创建设备类型
device_types = [
    {'name': 'Windows PC', 'category': '桌面设备', 'description': 'Windows操作系统个人电脑'},
    {'name': 'MacBook', 'category': '桌面设备', 'description': 'macOS操作系统笔记本电脑'},
    {'name': 'Android手机', 'category': '移动设备', 'description': 'Android系统智能手机'},
    {'name': 'iPhone', 'category': '移动设备', 'description': 'iOS系统智能手机'},
    {'name': 'iPad', 'category': '平板设备', 'description': 'iOS系统平板电脑'},
]

for device_data in device_types:
    device, created = DeviceType.objects.get_or_create(
        name=device_data['name'],
        defaults=device_data
    )
    if created:
        print(f'已添加设备类型: {device_data["name"]}')

print('初始数据创建完成!') 