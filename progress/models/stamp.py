from django.db import models
from django.conf import settings
from django.utils import timezone
from .progress import DailyProgress


class StampType(models.Model):
    """スタンプの種類を定義するモデル"""
    
    name = models.CharField(max_length=50, verbose_name='スタンプ名')
    emoji = models.CharField(max_length=10, verbose_name='絵文字')
    color = models.CharField(max_length=20, verbose_name='色', default='blue')
    description = models.TextField(blank=True, verbose_name='説明')
    order = models.IntegerField(default=0, verbose_name='表示順')
    is_active = models.BooleanField(default=True, verbose_name='有効')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'スタンプ種類'
        verbose_name_plural = 'スタンプ種類'
    
    def __str__(self):
        return f"{self.emoji} {self.name}"


class Stamp(models.Model):
    """日報に押されたスタンプのレコード"""
    
    daily_progress = models.ForeignKey(
        DailyProgress,
        on_delete=models.CASCADE,
        related_name='stamps',
        verbose_name='日報'
    )
    stamp_type = models.ForeignKey(
        StampType,
        on_delete=models.CASCADE,
        verbose_name='スタンプ種類'
    )
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='given_stamps',
        verbose_name='スタンプを押した管理者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='押された日時')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'スタンプ'
        verbose_name_plural = 'スタンプ'
        # 同じ管理者が同じ日報に複数のスタンプを押せないようにする（一人一投稿一スタンプ）
        unique_together = [['daily_progress', 'admin_user']]
    
    def __str__(self):
        return f"{self.stamp_type} on {self.daily_progress} by {self.admin_user}"