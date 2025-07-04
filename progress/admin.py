from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django import forms
from django.db import models
from .models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats, StampType, Stamp


class CustomUserCreationForm(forms.ModelForm):
    """新規ユーザー作成時に研修情報も設定できるフォーム"""
    password1 = forms.CharField(label='パスワード', widget=forms.PasswordInput)
    password2 = forms.CharField(label='パスワード(確認)', widget=forms.PasswordInput)
    
    # 研修情報の初期設定フィールド
    initial_phase = forms.ModelChoiceField(
        queryset=Phase.objects.all(),
        required=False,
        label='開始フェーズ',
        help_text='研修生の場合、開始フェーズを選択してください'
    )
    initial_item = forms.ModelChoiceField(
        queryset=CurriculumItem.objects.all(),
        required=False,
        label='開始項目',
        help_text='研修生の場合、開始項目を選択してください'
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'user_type', 'group', 'start_date')
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("パスワードが一致しません")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            
            # 研修生の場合、初期進捗と統計を作成
            if user.user_type == 'student':
                initial_phase = self.cleaned_data.get('initial_phase', Phase.objects.filter(phase_number=1).first())
                initial_item = self.cleaned_data.get('initial_item', CurriculumItem.objects.filter(phase=initial_phase).order_by('order').first())
                
                # UserStatsを作成
                UserStats.objects.create(
                    user=user,
                    current_phase=initial_phase,
                    current_item=initial_item,
                    current_grade='D'
                )
                
                # 初日の進捗を作成
                from datetime import date
                DailyProgress.objects.create(
                    user=user,
                    date=date.today(),
                    current_phase=initial_phase,
                    current_item=initial_item,
                    current_grade='D',
                    study_hours=0
                )
        return user


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    list_display = ('username', 'email', 'user_type', 'group', 'start_date', 'is_staff', 'training_edit_link')
    list_filter = ('user_type', 'group', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('追加情報', {'fields': ('user_type', 'group', 'start_date')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type', 'group', 'start_date', 'initial_phase', 'initial_item'),
        }),
    )
    
    def training_edit_link(self, obj):
        if obj.user_type == 'student':
            url = reverse('edit_user_training', kwargs={'user_id': obj.pk})
            return format_html('<a href="{}" class="button" style="background-color: #9F7AEA; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">研修編集</a>', url)
        return '-'
    training_edit_link.short_description = '研修編集'
    training_edit_link.allow_tags = True


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


class DailyProgressAdminForm(forms.ModelForm):
    """進捗記録の追加・編集フォーム"""
    class Meta:
        model = DailyProgress
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 研修生のみをユーザー選択肢に表示
        self.fields['user'].queryset = CustomUser.objects.filter(user_type='student')
        
        # フェーズ選択時に関連する項目のみ表示するようJavaScriptで制御
        if 'current_phase' in self.data:
            try:
                phase_id = int(self.data.get('current_phase'))
                self.fields['current_item'].queryset = CurriculumItem.objects.filter(phase_id=phase_id).order_by('order')
            except (ValueError, TypeError):
                pass
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        if commit:
            # UserStatsを自動更新
            user_stats, created = UserStats.objects.get_or_create(user=instance.user)
            
            # 最新の進捗を反映
            latest_progress = DailyProgress.objects.filter(user=instance.user).order_by('-date').first()
            if latest_progress:
                user_stats.current_phase = latest_progress.current_phase
                user_stats.current_item = latest_progress.current_item
                user_stats.current_grade = latest_progress.current_grade
                
                # 累計学習時間を再計算
                total_hours = DailyProgress.objects.filter(user=instance.user).aggregate(
                    total=models.Sum('study_hours')
                )['total'] or 0
                user_stats.total_study_hours = total_hours
                
                # 完了率を計算
                user_stats.calculate_completion_rate()
                user_stats.save()
        
        return instance


@admin.register(DailyProgress)
class DailyProgressAdmin(admin.ModelAdmin):
    form = DailyProgressAdminForm
    list_display = ('user', 'date', 'current_phase', 'current_item', 'study_hours', 'current_grade', 'feedback_requested')
    list_filter = ('current_phase', 'current_grade', 'feedback_requested', 'date')
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'date'
    
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'date', 'study_hours')
        }),
        ('進捗情報', {
            'fields': ('current_phase', 'current_item', 'current_grade')
        }),
        ('フィードバック', {
            'fields': ('feedback_requested', 'feedback_content', 'specific_problem', 'tried_solutions'),
            'classes': ('collapse',)
        }),
        ('メモ', {
            'fields': ('memo', 'admin_memo'),
            'classes': ('collapse',)
        }),
    )
    
    # 追加画面での初期値設定
    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        from datetime import date
        initial['date'] = date.today()
        initial['current_grade'] = 'D'
        return initial
    
    # インライン編集を有効化
    list_editable = ('study_hours', 'current_grade')
    
    # アクションを追加
    actions = ['mark_feedback_resolved']
    
    def mark_feedback_resolved(self, request, queryset):
        queryset.update(feedback_requested=False)
        self.message_user(request, f"{queryset.count()}件のフィードバックを解決済みにしました。")
    mark_feedback_resolved.short_description = "選択した進捗のフィードバックを解決済みにする"


@admin.register(UserStats)
class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_study_hours', 'current_phase', 'current_grade', 'days_elapsed', 'completion_rate')
    list_filter = ('current_grade', 'current_phase')
    readonly_fields = ('last_updated',)


@admin.register(StampType)
class StampTypeAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'name', 'color', 'order', 'is_active')
    list_filter = ('is_active',)
    ordering = ('order',)


@admin.register(Stamp)
class StampAdmin(admin.ModelAdmin):
    list_display = ('stamp_type', 'daily_progress', 'admin_user', 'created_at')
    list_filter = ('stamp_type', 'created_at')
    search_fields = ('daily_progress__user__username', 'admin_user__username')
    date_hierarchy = 'created_at'
