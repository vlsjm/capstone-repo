# Generated by Django 5.2 on 2025-06-01 16:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_propertycategory_alter_property_category'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='supply',
            options={'permissions': [('view_admin_dashboard', 'Can view  admin dashboard'), ('view_checkout_page', 'Can view checkout page'), ('view_user_dashboard', 'Can view user dashboard'), ('view_user_module', 'Can view user module'), ('view_admin_module', 'Can view admin module')]},
        ),
    ]
