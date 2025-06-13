from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class CustomUser(AbstractUser):
    USER_TYPES = [
        ('student', '研修生'),
        ('admin', '管理者'),
    ]
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='student')
    group = models.ForeignKey('Group', on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField(null=True, blank=True, verbose_name='研修開始日')
    
    class Meta:
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'


class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name='グループ名')
    description = models.TextField(blank=True, verbose_name='説明')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'グループ'
        verbose_name_plural = 'グループ'


class Phase(models.Model):
    PHASE_CHOICES = [
        (1, 'Phase 1: フロントエンド基礎1'),
        (2, 'Phase 2: フロントエンド基礎2'),
        (3, 'Phase 3: フロントエンド実践'),
        (4, 'Phase 4: サーバーサイド基礎1'),
        (5, 'Phase 5: サーバーサイド基礎2'),
        (6, 'Phase 6: サーバーサイド実践'),
        (7, 'Phase 7: WEBシステム自作'),
    ]
    
    phase_number = models.IntegerField(choices=PHASE_CHOICES, unique=True, verbose_name='Phase番号')
    name = models.CharField(max_length=100, verbose_name='Phase名')
    description = models.TextField(blank=True, verbose_name='説明')
    total_days = models.IntegerField(verbose_name='標準日数')
    start_day = models.IntegerField(verbose_name='開始日（カリキュラム全体の何日目）')
    end_day = models.IntegerField(verbose_name='終了日（カリキュラム全体の何日目）')
    
    def __str__(self):
        return f"Phase {self.phase_number}: {self.name}"
    
    class Meta:
        verbose_name = 'Phase'
        verbose_name_plural = 'Phase'
        ordering = ['phase_number']


class CurriculumItem(models.Model):
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='items')
    item_code = models.CharField(max_length=10, verbose_name='項目コード')
    name = models.CharField(max_length=200, verbose_name='項目名')
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, verbose_name='標準時間')
    estimated_days = models.IntegerField(null=True, blank=True, verbose_name='標準日数')
    order = models.IntegerField(verbose_name='順序')
    description = models.TextField(blank=True, verbose_name='説明')
    
    def __str__(self):
        return f"{self.item_code}: {self.name}"
    
    class Meta:
        verbose_name = 'カリキュラム項目'
        verbose_name_plural = 'カリキュラム項目'
        ordering = ['phase__phase_number', 'order']
        unique_together = ['phase', 'item_code']


class DailyProgress(models.Model):
    GRADE_CHOICES = [
        ('S', 'S級 (120日以内)'),
        ('A', 'A級 (150日以内)'),
        ('B', 'B級 (180日以内)'),
        ('C', 'C級 (210日以内)'),
        ('D', 'D級 (210日超過)'),
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
    
    reflection = models.TextField(max_length=300, verbose_name='今日の振り返り')
    next_goal = models.TextField(max_length=200, verbose_name='明日の目標')
    next_phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='next_progress', null=True, blank=True, verbose_name='予定Phase')
    next_item = models.ForeignKey(CurriculumItem, on_delete=models.CASCADE, related_name='next_progress', null=True, blank=True, verbose_name='予定項目')
    planned_hours = models.DecimalField(max_digits=4, decimal_places=1, verbose_name='予定学習時間')
    
    action_plan = models.TextField(max_length=200, verbose_name='具体的な行動計画')
    need_review = models.BooleanField(default=False, verbose_name='復習必要')
    have_question = models.BooleanField(default=False, verbose_name='質問予定')
    next_phase_ready = models.BooleanField(default=False, verbose_name='次Phase進行予定')
    
    current_grade = models.CharField(max_length=1, choices=GRADE_CHOICES, verbose_name='現在の階級')
    days_elapsed = models.IntegerField(verbose_name='経過日数')
    delay_days = models.IntegerField(default=0, verbose_name='遅れ日数')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.date} - {self.current_item}"
    
    class Meta:
        verbose_name = '日次進捗記録'
        verbose_name_plural = '日次進捗記録'
        unique_together = ['user', 'date']
        ordering = ['-date']


class UserStats(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='stats')
    total_study_hours = models.DecimalField(max_digits=7, decimal_places=1, default=0, verbose_name='累計学習時間')
    current_phase = models.ForeignKey(Phase, on_delete=models.CASCADE, null=True, verbose_name='現在のPhase')
    current_item = models.ForeignKey(CurriculumItem, on_delete=models.CASCADE, null=True, verbose_name='現在の項目')
    current_grade = models.CharField(max_length=1, choices=DailyProgress.GRADE_CHOICES, default='A', verbose_name='現在の階級')
    days_elapsed = models.IntegerField(default=0, verbose_name='経過日数')
    delay_days = models.IntegerField(default=0, verbose_name='遅れ日数')
    stars = models.IntegerField(default=0, verbose_name='星の数')
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='完了率')
    estimated_completion_date = models.DateField(null=True, blank=True, verbose_name='完了見込み日')
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'ユーザー統計'
        verbose_name_plural = 'ユーザー統計'
