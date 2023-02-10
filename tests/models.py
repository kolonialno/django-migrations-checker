from django.db import models


class Order(models.Model):
    number = models.PositiveIntegerField(unique=True)


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    class Meta:
        indexes = [
            models.Index(fields=["order"], name="order"),
        ]
