# Generated by Django 5.0.1 on 2025-07-04 10:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0010_alert'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='stamp',
            unique_together={('daily_progress', 'admin_user')},
        ),
    ]
