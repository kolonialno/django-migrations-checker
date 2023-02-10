# Generated by Django 4.1.6 on 2023-02-10 00:55

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tests", "0003_alter_order_number"),
    ]

    operations = [
        AddIndexConcurrently(
            model_name="orderline",
            index=models.Index(fields=["order"], name="order"),
        ),
    ]
