# Generated by Django 5.2.1 on 2025-05-28 17:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_alter_supply_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='supply',
            name='quantity',
        ),
        migrations.CreateModel(
            name='SupplyQuantity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_quantity', models.PositiveIntegerField(default=0)),
                ('minimum_threshold', models.PositiveIntegerField(default=10)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('supply', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='quantity_info', to='app.supply')),
            ],
        ),
    ]
