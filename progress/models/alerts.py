from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta

User = get_user_model()


class Alert(models.Model):
    """アラートモデル"""
    
    ALERT_TYPES = [
        ('grade_risk', '階級降格リスク'),
        ('no_report', '日報未提出'),
        ('long_delay', '大幅遅れ'),
        ('feedback_request', 'フィードバック要請'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', '軽微'),
        ('medium', '注意'),
        ('high', '重要'),
        ('critical', '緊急'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['alert_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_alert_type_display()} ({self.get_severity_display()})"
    
    def get_severity_color(self):
        """重要度に応じた色を返す"""
        colors = {
            'low': 'blue',
            'medium': 'yellow',
            'high': 'orange',
            'critical': 'red'
        }
        return colors.get(self.severity, 'gray')
    
    def get_severity_icon(self):
        """重要度に応じたアイコンを返す"""
        icons = {
            'low': 'ℹ️',
            'medium': '⚠️',
            'high': '🚨',
            'critical': '🔥'
        }
        return icons.get(self.severity, '📝')
    
    def resolve(self, resolved_by=None):
        """アラートを解決済みにする"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if resolved_by:
            self.resolved_by = resolved_by
        self.save()
    
    @classmethod
    def create_grade_risk_alert(cls, user, current_grade, risk_grade, days_behind):
        """階級降格リスクアラートを作成"""
        title = f"階級降格リスク: {current_grade}級 → {risk_grade}級"
        message = f"現在の進捗遅れ（{days_behind}日）により、{risk_grade}級に降格する可能性があります。"
        
        severity = 'critical' if days_behind >= 10 else 'high'
        
        # 同じユーザーの同じタイプのアクティブなアラートがある場合は更新
        existing_alert = cls.objects.filter(
            user=user,
            alert_type='grade_risk',
            is_active=True,
            is_resolved=False
        ).first()
        
        if existing_alert:
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.severity = severity
            existing_alert.save()
            return existing_alert
        else:
            return cls.objects.create(
                user=user,
                alert_type='grade_risk',
                severity=severity,
                title=title,
                message=message
            )
    
    @classmethod
    def create_no_report_alert(cls, user, days_missing):
        """日報未提出アラートを作成"""
        title = f"日報未提出: {days_missing}日間"
        message = f"過去{days_missing}日間、日報が提出されていません。定期的な進捗報告をお願いします。"
        
        if days_missing >= 7:
            severity = 'critical'
        elif days_missing >= 5:
            severity = 'high'
        else:
            severity = 'medium'
        
        # 同じユーザーの同じタイプのアクティブなアラートがある場合は更新
        existing_alert = cls.objects.filter(
            user=user,
            alert_type='no_report',
            is_active=True,
            is_resolved=False
        ).first()
        
        if existing_alert:
            existing_alert.title = title
            existing_alert.message = message
            existing_alert.severity = severity
            existing_alert.save()
            return existing_alert
        else:
            return cls.objects.create(
                user=user,
                alert_type='no_report',
                severity=severity,
                title=title,
                message=message
            )