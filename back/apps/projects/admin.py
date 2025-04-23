from django.contrib import admin
from .models import Project, ProjectTag, ProjectMember, Milestone, Environment, ProjectDocument


@admin.register(ProjectTag)
class ProjectTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'description', 'created_at')
    search_fields = ('name', 'description')


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1
    fields = ('user', 'role', 'is_active', 'can_manage_members', 'can_manage_test_cases', 'can_manage_executions')


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 1
    fields = ('name', 'status', 'start_date', 'due_date', 'completed_date')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'status', 'priority', 'manager', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('name', 'code', 'description')
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'updated_at', 'test_case_count', 'bug_count')
    inlines = [ProjectMemberInline, MilestoneInline]
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'code', 'description', 'status', 'priority')
        }),
        ('日期信息', {
            'fields': ('start_date', 'end_date', 'created_at', 'updated_at')
        }),
        ('关联人员', {
            'fields': ('creator', 'manager')
        }),
        ('标签', {
            'fields': ('tags',)
        }),
        ('统计数据', {
            'fields': ('test_case_count', 'bug_count')
        }),
    )


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active', 'joined_at')
    search_fields = ('project__name', 'user__username', 'user__name')


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'start_date', 'due_date', 'completed_date')
    list_filter = ('status', 'start_date', 'due_date')
    search_fields = ('name', 'description', 'project__name')


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'server_url', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description', 'project__name', 'server_url')


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'doc_type', 'version', 'created_by', 'created_at')
    list_filter = ('doc_type', 'created_at')
    search_fields = ('title', 'description', 'content', 'project__name')
    readonly_fields = ('created_at', 'updated_at')
