from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name='グループ名')
    description = models.TextField(blank=True, verbose_name='説明')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'グループ'
        verbose_name_plural = 'グループ'