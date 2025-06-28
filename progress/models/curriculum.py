from django.db import models


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