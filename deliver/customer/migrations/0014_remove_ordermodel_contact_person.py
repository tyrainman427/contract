# Generated by Django 4.2.2 on 2023-09-21 06:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0013_remove_ordermodel_telephone_number'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ordermodel',
            name='contact_person',
        ),
    ]
