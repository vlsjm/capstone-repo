# Generated by Django 5.2.1 on 2025-05-26 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0009_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='borrowrequest',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='damagereport',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supplyrequest',
            name='remarks',
            field=models.TextField(blank=True, null=True),
        ),
    ]
