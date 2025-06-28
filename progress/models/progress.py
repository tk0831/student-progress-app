from django.db import models
from .user import CustomUser
from .curriculum import Phase, CurriculumItem


class DailyProgress(models.Model):
    GRADE_CHOICES = [
        ('S', 'S級 (速度120%以上)'),
        ('A', 'A級 (速度100%以上)'),
        ('B', 'B級 (速度80%以上)'),
        ('C', 'C級 (速度60%以上)'),
        ('D', 'D級 (速度60%未満)'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='daily_progress')
    date = models.DateField(verbose_name='記録日')
    current_phase = models.ForeignKey(Phase, on_delete=models.CASCADE, verbose_name='現在のPhase')
    current_item = models.ForeignKey(CurriculumItem, on_delete=models.CASCADE, verbose_name='現在の項目')
    progress_detail = models.TextField(max_length=100, blank=True, verbose_name='進捗詳細')
    
    study_hours = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='本日の学習時間')
    stuck_content = models.TextField(max_length=500, blank=True, verbose_name='詰まった内容')
    feedback_requested = models.BooleanField(default=False, verbose_name='フィードバック希望')
    problem_detail = models.TextField(max_length=300, blank=True, verbose_name='具体的な問題内容')
    tried_solutions = models.TextField(max_length=300, blank=True, verbose_name='試したこと')
    
    # フィードバック対応状況
    feedback_provided = models.BooleanField(default=False, verbose_name='フィードバック提供済み')
    feedback_admin = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='provided_feedback',
        verbose_name='フィードバック提供者',
        limit_choices_to={'user_type__in': ['training_admin', 'system_admin']}
    )
    feedback_response = models.TextField(max_length=1000, blank=True, verbose_name='フィードバック内容')
    feedback_provided_at = models.DateTimeField(null=True, blank=True, verbose_name='フィードバック提供日時')
    
    # ファイル添付
    attachment_file = models.FileField(
        upload_to='feedback_attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='添付ファイル（ZIP）',
        help_text='ZIP形式のファイルのみアップロード可能です'
    )
    
    reflection = models.TextField(max_length=300, verbose_name='今日の振り返り')
    next_goal = models.TextField(max_length=200, verbose_name='明日の目標')
    next_phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='next_progress', null=True, blank=True, verbose_name='予定Phase')
    next_item = models.ForeignKey(CurriculumItem, on_delete=models.CASCADE, related_name='next_progress', null=True, blank=True, verbose_name='予定項目')
    planned_hours = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='予定学習時間')
    
    action_plan = models.TextField(max_length=200, verbose_name='具体的な行動計画')
    need_review = models.BooleanField(default=False, verbose_name='復習必要')
    have_question = models.BooleanField(default=False, verbose_name='質問予定')
    next_phase_ready = models.BooleanField(default=False, verbose_name='次Phase進行予定')
    
    # 項目完了フラグ
    item_completed = models.BooleanField(default=False, verbose_name='項目完了')
    
    current_grade = models.CharField(max_length=1, choices=GRADE_CHOICES, verbose_name='現在の階級')
    days_elapsed = models.IntegerField(verbose_name='経過日数')
    delay_days = models.IntegerField(default=0, verbose_name='遅れ日数')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def feedback_status(self):
        """フィードバック状況を返す"""
        if not self.feedback_requested:
            return 'no_request'  # フィードバック要請なし
        elif self.feedback_provided:
            return 'completed'   # 対応完了
        else:
            return 'pending'     # 対応待ち
    
    @property
    def feedback_status_display(self):
        """フィードバック状況の表示名"""
        status_map = {
            'no_request': 'フィードバック要請なし',
            'pending': '対応待ち',
            'completed': '対応完了'
        }
        return status_map.get(self.feedback_status, '不明')

    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.current_item}"
    
    class Meta:
        verbose_name = '日次進捗記録'
        verbose_name_plural = '日次進捗記録'
        unique_together = ['user', 'date']
        ordering = ['-date']