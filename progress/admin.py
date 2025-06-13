from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'group', 'start_date', 'is_staff')
    list_filter = ('user_type', 'group', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('追加情報', {'fields': ('user_type', 'group', 'start_date')}),
    )


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = ('phase_number', 'name', 'total_days', 'start_day', 'end_day')
    ordering = ('phase_number',)


@admin.register(CurriculumItem)
class CurriculumItemAdmin(admin.ModelAdmin):
    list_display = ('item_code', 'name', 'phase', 'estimated_hours', 'estimated_days', 'order')
    list_filter = ('phase',)
    ordering = ('phase__phase_number', 'order')


@admin.register(DailyProgress)
class DailyProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'current_phase', 'current_item', 'study_hours', 'current_grade')
    list_filter = ('current_phase', 'current_grade', 'feedback_requested', 'date')
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_study_hours', 'current_phase', 'current_grade', 'days_elapsed', 'completion_rate')
    list_filter = ('current_grade', 'current_phase')
    readonly_fields = ('last_updated',)
