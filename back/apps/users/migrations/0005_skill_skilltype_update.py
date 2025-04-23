# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def link_skills_to_types(apps, schema_editor):
    """将已存在的技能关联到适当的技能类型"""
    Skill = apps.get_model('users', 'Skill')
    SkillType = apps.get_model('users', 'SkillType')
    
    # 创建默认技能类型映射
    default_types = {
        '编程语言': {
            'name': '编程语言',
            'category': '技术',
            'description': '各种编程语言技能',
            'order': 10
        },
        '框架': {
            'name': '框架',
            'category': '技术',
            'description': '各类开发框架',
            'order': 20
        },
        '数据库': {
            'name': '数据库',
            'category': '技术',
            'description': '数据库相关技能',
            'order': 30
        },
        '前端技术': {
            'name': '前端技术',
            'category': '技术',
            'description': '前端开发相关技能',
            'order': 40
        },
        '后端技术': {
            'name': '后端技术',
            'category': '技术',
            'description': '后端开发相关技能',
            'order': 50
        },
        '测试': {
            'name': '测试',
            'category': '技术',
            'description': '软件测试相关技能',
            'order': 60
        },
        '设计': {
            'name': '设计',
            'category': '设计',
            'description': '设计相关技能',
            'order': 70
        },
        '管理': {
            'name': '管理',
            'category': '管理',
            'description': '项目管理相关技能',
            'order': 80
        },
        '其他': {
            'name': '其他',
            'category': '其他',
            'description': '其他技能类型',
            'order': 999
        }
    }
    
    # 创建技能类型字典，用于后续关联
    type_map = {}
    for key, data in default_types.items():
        skill_type, _ = SkillType.objects.get_or_create(
            name=key,
            defaults=data
        )
        type_map[key] = skill_type
    
    # 匹配规则 - 将技能的category映射到技能类型
    category_to_type = {
        'python': '编程语言',
        'java': '编程语言',
        'c++': '编程语言',
        'javascript': '编程语言',
        'typescript': '编程语言',
        'html': '前端技术',
        'css': '前端技术',
        'django': '框架',
        'flask': '框架',
        'spring': '框架',
        'vue': '框架',
        'react': '框架',
        'angular': '框架',
        'mysql': '数据库',
        'postgresql': '数据库',
        'mongodb': '数据库',
        'redis': '数据库',
        'git': '开发工具',
        'docker': '开发工具',
        'kubernetes': '开发工具',
        'ui': '设计',
        'ux': '设计',
        '设计': '设计',
        '测试': '测试',
        '单元测试': '测试',
        '集成测试': '测试',
        '性能测试': '测试',
        '项目管理': '管理',
        '团队管理': '管理',
        '管理': '管理',
        '沟通': '软技能',
        '演讲': '软技能',
        '写作': '软技能'
    }
    
    # 遍历所有技能，将其关联到适当的技能类型
    for skill in Skill.objects.all():
        # 尝试通过技能名和分类查找匹配的类型
        skill_name_lower = skill.name.lower()
        skill_category_lower = skill.category.lower()
        
        skill_type = None
        
        # 首先检查技能名称中是否包含任何关键词
        for keyword, type_name in category_to_type.items():
            if keyword in skill_name_lower or keyword in skill_category_lower:
                skill_type = type_map.get(type_name)
                if skill_type:
                    break
        
        # 如果没找到匹配项，根据分类直接匹配
        if not skill_type and skill.category in type_map:
            skill_type = type_map[skill.category]
        
        # 如果还是没找到，使用"其他"类型
        if not skill_type:
            skill_type = type_map['其他']
        
        # 更新技能记录
        skill.skill_type = skill_type
        skill.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_device_devicetype_migration'),
    ]

    operations = [
        # 为SkillType添加新字段
        migrations.AddField(
            model_name='skilltype',
            name='category',
            field=models.CharField(blank=True, max_length=50, verbose_name='分类'),
        ),
        migrations.AddField(
            model_name='skilltype',
            name='icon',
            field=models.CharField(blank=True, max_length=50, verbose_name='图标'),
        ),
        migrations.AddField(
            model_name='skilltype',
            name='order',
            field=models.IntegerField(default=0, verbose_name='排序值'),
        ),
        # 修改排序
        migrations.AlterModelOptions(
            name='skilltype',
            options={'ordering': ['order', 'name'], 'verbose_name': '技能类型', 'verbose_name_plural': '技能类型'},
        ),
        # 为Skill添加外键关联
        migrations.AddField(
            model_name='skill',
            name='skill_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='skills', to='users.skilltype', verbose_name='技能类型'),
        ),
        # 执行数据迁移函数，关联已有技能到技能类型
        migrations.RunPython(link_skills_to_types),
    ] 