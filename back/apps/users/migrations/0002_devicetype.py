# Generated by Django 4.2.20 on 2025-04-16 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeviceType",
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
                        max_length=50, unique=True, verbose_name="类型名称"
                    ),
                ),
                ("category", models.CharField(max_length=50, verbose_name="分类")),
                ("description", models.TextField(blank=True, verbose_name="描述")),
            ],
            options={
                "verbose_name": "设备类型",
                "verbose_name_plural": "设备类型",
            },
        ),
    ]
