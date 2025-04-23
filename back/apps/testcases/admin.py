from django.contrib import admin
from .models import Module, Tag, TestCase, TestCaseVersion, TestCaseStep # 确保导入 Tag

# Register your models here.

# 可以为模型定义更复杂的 Admin 类来自定义显示
# class TagAdmin(admin.ModelAdmin):
#     list_display = ('name',)
#     search_fields = ('name',)

# class ModuleAdmin(admin.ModelAdmin):
#     list_display = ('name', 'project', 'parent', 'created_at')
#     list_filter = ('project',)
#     search_fields = ('name', 'description')

# class TestCaseAdmin(admin.ModelAdmin):
#     list_display = ('title', 'project', 'module', 'status', 'created_by', 'updated_at')
#     list_filter = ('project', 'status', 'created_by')
#     search_fields = ('title',)

# 简单的注册
admin.site.register(Tag) # 注册 Tag 模型
admin.site.register(Module)
admin.site.register(TestCase)
admin.site.register(TestCaseVersion)
admin.site.register(TestCaseStep)
