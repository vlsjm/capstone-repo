# Generated by Django 5.2 on 2025-05-30 08:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0023_propertyhistory_remarks_supplyhistory_remarks'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='original_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='supplyquantity',
            name='original_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
