# Generated manually

from django.db import migrations, models
import django.db.models.deletion


def migrate_device_types(apps, schema_editor):
    """将device_type字符串转换为DeviceType外键关联"""
    Device = apps.get_model('users', 'Device')
    DeviceType = apps.get_model('users', 'DeviceType')
    
    # 首先，创建默认的设备类型
    default_types = {
        'pc': {'name': 'pc', 'category': '个人电脑', 'description': '个人电脑设备'},
        'mobile': {'name': 'mobile', 'category': '移动设备', 'description': '手机等移动设备'},
        'tablet': {'name': 'tablet', 'category': '平板设备', 'description': '平板电脑等设备'},
        'other': {'name': 'other', 'category': '其他设备', 'description': '其他类型设备'}
    }
    
    # 创建默认类型
    device_type_map = {}
    for key, data in default_types.items():
        device_type, _ = DeviceType.objects.get_or_create(
            name=key,
            defaults=data
        )
        device_type_map[key] = device_type
    
    # 查找不在默认类型中的自定义类型
    custom_types = Device.objects.values_list('device_type', flat=True).distinct()
    
    # 创建自定义类型
    for device_type_name in custom_types:
        if device_type_name not in device_type_map:
            device_type, _ = DeviceType.objects.get_or_create(
                name=device_type_name,
                defaults={
                    'category': '用户自定义',
                    'description': f'自动迁移的设备类型: {device_type_name}'
                }
            )
            device_type_map[device_type_name] = device_type
    
    # 更新所有设备
    for device in Device.objects.all():
        # 查找对应的DeviceType对象
        device_type = device_type_map.get(device.device_type)
        
        if device_type:
            # 保存旧的device_type值到legacy字段
            device.device_type_legacy = device.device_type
            # 更新为新的外键关系
            device.device_type = device_type
            device.save()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_skilltype'),
    ]

    operations = [
        # 添加临时字段
        migrations.AddField(
            model_name='device',
            name='device_type_legacy',
            field=models.CharField(blank=True, choices=[('pc', '个人电脑'), ('mobile', '移动设备'), ('tablet', '平板设备'), ('other', '其他设备')], max_length=20, null=True, verbose_name='设备类型(旧)'),
        ),
        # 添加device_type外键字段，允许为空，以便迁移
        migrations.AddField(
            model_name='device',
            name='device_type_new',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='devices', to='users.devicetype', verbose_name='设备类型'),
        ),
        # 运行迁移数据的函数
        migrations.RunPython(migrate_device_types),
        # 删除旧的device_type字段
        migrations.RemoveField(
            model_name='device',
            name='device_type',
        ),
        # 重命名新字段为device_type
        migrations.RenameField(
            model_name='device',
            old_name='device_type_new',
            new_name='device_type',
        ),
        # 将device_type设为非空
        migrations.AlterField(
            model_name='device',
            name='device_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='devices', to='users.devicetype', verbose_name='设备类型'),
        ),
    ] 