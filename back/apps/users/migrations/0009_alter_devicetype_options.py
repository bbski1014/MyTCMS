# Generated by Django 4.2.20 on 2025-04-19 07:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_alter_device_additional_info_alter_device_browser_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="devicetype",
            options={
                "ordering": ["id"],
                "verbose_name": "设备类型",
                "verbose_name_plural": "设备类型",
            },
        ),
    ]
