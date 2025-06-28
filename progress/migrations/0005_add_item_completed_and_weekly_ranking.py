# Generated manually for item completion and weekly ranking features

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0004_customuser_assigned_admin_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyprogress',
            name='item_completed',
            field=models.BooleanField(default=False, verbose_name='項目完了'),
        ),
        migrations.CreateModel(
            name='WeeklyRanking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField(verbose_name='週開始日')),
                ('week_end', models.DateField(verbose_name='週終了日')),
                ('rank', models.IntegerField(verbose_name='順位')),
                ('completed_standard_days', models.IntegerField(verbose_name='完了項目標準日数合計')),
                ('efficiency_score', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='進捗効率スコア')),
                ('total_study_hours', models.DecimalField(decimal_places=1, max_digits=6, verbose_name='総学習時間')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_rankings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '週間ランキング',
                'verbose_name_plural': '週間ランキング',
                'ordering': ['-week_start', 'rank'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='weeklyranking',
            unique_together={('user', 'week_start')},
        ),
    ]