# Generated by Django 4.2.2 on 2023-09-21 04:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0011_remove_ordermodel_address_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='menuitem',
            name='max_quantity',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]