# Generated by Django 5.2.1 on 2025-06-03 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_alter_supplysubcategory_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supply',
            name='barcode',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
