from django.db import models

from airport.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid"
        NOT_PAID = "not paid"

    status = models.CharField(max_length=10, choices=Status.choices)
    order = models.ForeignKey(Order, on_delete=models.DO_NOTHING)
    session_url = models.CharField(max_length=255)
    session_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
