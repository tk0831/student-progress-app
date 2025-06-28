from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    USER_TYPES = [
        ('student', '研修生'),
        ('training_admin', '研修管理者'),
        ('system_admin', 'システム管理者'),
    ]
    user_type = models.CharField(max_length=15, choices=USER_TYPES, default='student')
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, verbose_name='研修開始日')
    
    # 担当研修管理者（研修生のみ設定可能）
    assigned_admin = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_students',
        verbose_name='担当研修管理者',
        limit_choices_to={'user_type': 'training_admin'}
    )
    
    # 権限フラグ
    can_manage_students = models.BooleanField(default=False, verbose_name='研修生管理権限')
    can_manage_curriculum = models.BooleanField(default=False, verbose_name='カリキュラム管理権限')
    can_manage_groups = models.BooleanField(default=False, verbose_name='グループ管理権限')
    can_view_analytics = models.BooleanField(default=False, verbose_name='分析画面閲覧権限')
    can_manage_system = models.BooleanField(default=False, verbose_name='システム管理権限')
    can_manage_users = models.BooleanField(default=False, verbose_name='ユーザー管理権限')
    
    def save(self, *args, **kwargs):
        # ユーザータイプに基づいて権限を自動設定
        if self.user_type == 'training_admin':
            self.can_manage_students = True
            self.can_manage_curriculum = True
            self.can_manage_groups = True
            self.can_view_analytics = True
            self.can_manage_system = False
            self.can_manage_users = False
        elif self.user_type == 'system_admin':
            self.can_manage_students = True
            self.can_manage_curriculum = True
            self.can_manage_groups = True
            self.can_view_analytics = True
            self.can_manage_system = True
            self.can_manage_users = True
            self.is_staff = True
            self.is_superuser = True
        elif self.user_type == 'student':
            self.can_manage_students = False
            self.can_manage_curriculum = False
            self.can_manage_groups = False
            self.can_view_analytics = False
            self.can_manage_system = False
            self.can_manage_users = False
            self.is_staff = False
            self.is_superuser = False
        
        super().save(*args, **kwargs)
    
    @property
    def is_training_admin(self):
        return self.user_type == 'training_admin'
    
    @property
    def is_system_admin(self):
        return self.user_type == 'system_admin'
    
    @property
    def display_user_type(self):
        return dict(self.USER_TYPES).get(self.user_type, self.user_type)
    
    def get_current_progress_status(self):
        """現在の進捗状況を取得"""
        if self.user_type != 'student':
            return None
            
        from .curriculum import Phase, CurriculumItem
        
        # 最新の進捗記録を取得
        latest_progress = self.daily_progress.order_by('-date').first()
        if not latest_progress:
            return {
                'current_phase': None,
                'current_item': None,
                'completed_phases': [],
                'available_phases': Phase.objects.all(),
                'available_items': CurriculumItem.objects.all()
            }
        
        # 完了したフェーズを特定
        completed_phases = []
        
        # 項目完了記録から完了したフェーズを判定
        completed_items = self.daily_progress.filter(item_completed=True).values_list('current_item_id', flat=True)
        
        for phase in Phase.objects.all().order_by('phase_number'):
            phase_items = CurriculumItem.objects.filter(phase=phase)
            phase_item_ids = set(phase_items.values_list('id', flat=True))
            completed_item_ids = set(completed_items)
            
            # フェーズ内の全ての項目が完了している場合、そのフェーズは完了
            if phase_item_ids.issubset(completed_item_ids) and phase_item_ids:
                completed_phases.append(phase.phase_number)
        
        # 利用可能なフェーズ（完了していないフェーズのみ）
        current_phase_number = latest_progress.current_phase.phase_number
        
        # 完了していないフェーズを取得
        all_phase_numbers = list(Phase.objects.values_list('phase_number', flat=True))
        available_phase_numbers = [num for num in all_phase_numbers if num not in completed_phases]
        
        available_phases = Phase.objects.filter(phase_number__in=available_phase_numbers)
        
        # 利用可能な項目（利用可能なフェーズの項目のみ）
        available_items = CurriculumItem.objects.filter(phase__in=available_phases)
        
        return {
            'current_phase': latest_progress.current_phase,
            'current_item': latest_progress.current_item,
            'completed_phases': completed_phases,
            'available_phases': available_phases,
            'available_items': available_items,
            'latest_progress': latest_progress
        }
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'