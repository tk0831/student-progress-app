# Generated by Django 5.0.1 on 2025-07-03 04:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0008_weeklystudyhoursranking'),
    ]

    operations = [
        migrations.CreateModel(
            name='StampType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='スタンプ名')),
                ('emoji', models.CharField(max_length=10, verbose_name='絵文字')),
                ('color', models.CharField(default='blue', max_length=20, verbose_name='色')),
                ('description', models.TextField(blank=True, verbose_name='説明')),
                ('order', models.IntegerField(default=0, verbose_name='表示順')),
                ('is_active', models.BooleanField(default=True, verbose_name='有効')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': 'スタンプ種類',
                'verbose_name_plural': 'スタンプ種類',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Stamp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='押された日時')),
                ('admin_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='given_stamps', to=settings.AUTH_USER_MODEL, verbose_name='スタンプを押した管理者')),
                ('daily_progress', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stamps', to='progress.dailyprogress', verbose_name='日報')),
                ('stamp_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='progress.stamptype', verbose_name='スタンプ種類')),
            ],
            options={
                'verbose_name': 'スタンプ',
                'verbose_name_plural': 'スタンプ',
                'ordering': ['-created_at'],
                'unique_together': {('daily_progress', 'stamp_type', 'admin_user')},
            },
        ),
    ]
