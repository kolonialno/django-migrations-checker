from django.db import models


class Order(models.Model):
    number = models.PositiveIntegerField(unique=True)


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.CheckConstraint(check=models.Q(order__gte=18), name="order_gte_18"),
        ]
