# Generated by Django 5.2.1 on 2025-06-03 17:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0034_supplycategory_supplysubcategory_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='supplycategory',
            options={'verbose_name_plural': 'Supply Categories'},
        ),
        migrations.AlterModelOptions(
            name='supplysubcategory',
            options={'verbose_name_plural': 'Supply Subcategories'},
        ),
        migrations.AddField(
            model_name='supplycategory',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supplysubcategory',
            name='category',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subcategories', to='app.supplycategory'),
        ),
        migrations.AddField(
            model_name='supplysubcategory',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='supply',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.supplycategory'),
        ),
        migrations.AlterField(
            model_name='supply',
            name='subcategory',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='app.supplysubcategory'),
        ),
        migrations.AlterField(
            model_name='supplysubcategory',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterUniqueTogether(
            name='supplysubcategory',
            unique_together={('name', 'category')},
        ),
    ]
