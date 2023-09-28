from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Type

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    RegexValidator,
    MinValueValidator,
    MaxValueValidator
)
from django.db import models
from django.utils.text import slugify


class UppercaseField(models.CharField):
    """This method ensures that CharField is saved in uppercase"""

    def get_prep_value(self, value: str) -> str:
        value = super().get_prep_value(value)
        return value if value is None else value.upper()


class AircraftManufacturer(models.Model):
    name = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name


class AircraftType(models.Model):
    name = models.CharField(max_length=55)
    manufacturer = models.ForeignKey(
        to=AircraftManufacturer,
        on_delete=models.CASCADE,
        related_name="aircraft"
    )

    def __str__(self) -> str:
        return self.name


def aircraft_image_file_path(instance: Aircraft, filename: str) -> str:
    _, extension = os.path.splitext(filename)
    filename = f"{slugify(instance.registration)}-{uuid.uuid4()}{extension}"
    return os.path.join("uploads/images/", filename)


class Aircraft(models.Model):
    registration = UppercaseField(max_length=10, unique=True)
    production_year = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(datetime.now().year)
        ],
        help_text="Use the following format: YYYY",
    )
    rows = models.IntegerField()
    seats_in_row = models.IntegerField()
    aircraft_type = models.ForeignKey(
        to=AircraftType, on_delete=models.CASCADE, related_name="aircraft"
    )
    image = models.ImageField(null=True, upload_to=aircraft_image_file_path)

    class Meta:
        verbose_name_plural = "aircraft"

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    @property
    def age(self) -> int:
        return datetime.now().year - self.production_year

    def __str__(self) -> str:
        return self.registration


class Airline(models.Model):
    name = models.CharField(max_length=100, unique=True)
    iata_code = UppercaseField(max_length=2, unique=True, blank=True)
    icao_code = UppercaseField(max_length=3, unique=True, blank=True)
    callsign = UppercaseField(max_length=50, unique=True, blank=True)
    country = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Airport(models.Model):
    iata_code = UppercaseField(max_length=3, unique=True, blank=True)
    icao_code = UppercaseField(max_length=4, unique=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    nearest_city = models.CharField(max_length=155)
    info = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.iata_code} ({self.nearest_city})"


class Crew(models.Model):
    first_name = models.CharField(max_length=55)
    last_name = models.CharField(max_length=55)
    license_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[
            RegexValidator(
                r"[A-Z]{3}[0-9]{5}",
                "License should start with 3 capital letters "
                "followed by min 5 digits",
            )
        ],
    )

    class Meta:
        verbose_name_plural = "crew"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Route(models.Model):
    source = models.ForeignKey(
        to=Airport,
        on_delete=models.CASCADE,
        related_name="source"
    )
    destination = models.ForeignKey(
        to=Airport,
        on_delete=models.CASCADE,
        related_name="destination"
    )
    distance = models.IntegerField()

    class Meta:
        unique_together = ("source", "destination")

    @property
    def route_name(self) -> str:
        return f"{self.source.iata_code} - {self.destination.iata_code}"

    def __str__(self) -> str:
        return f"{self.source} - {self.destination}"


class Flight(models.Model):
    class Status(models.TextChoices):
        ON_TIME = "on_time"
        DELAYED = "delayed"
        CANCELLED = "cancelled"

    flight_number = models.CharField(max_length=55)
    airline = models.ForeignKey(
        to=Airline,
        on_delete=models.CASCADE,
        related_name="flights"
    )
    route = models.ForeignKey(
        to=Route,
        on_delete=models.CASCADE,
        related_name="flights"
    )
    aircraft = models.ForeignKey(
        to=Aircraft,
        on_delete=models.CASCADE,
        related_name="flights"
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, related_name="flights")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ON_TIME
    )

    def __str__(self) -> str:
        return f"{self.flight_number} ({self.departure_time})"


class Order(models.Model):

    class PaidChoices(models.TextChoices):
        PAID = "paid"
        NOT_PAID = "not paid"

    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=50, choices=PaidChoices.choices, default=PaidChoices.NOT_PAID)

    def __str__(self) -> str:
        return self.created_at.strftime("%Y-%m-%d, %H:%M:%S")

    @property
    def route_name(self) -> str:
        return self.tickets.first().flight.route


class Ticket(models.Model):
    row = models.IntegerField()
    seat = UppercaseField(max_length=1)
    flight = models.ForeignKey(
        to=Flight,
        on_delete=models.CASCADE,
        related_name="tickets"
    )
    order = models.ForeignKey(
        to=Order,
        on_delete=models.CASCADE,
        related_name="tickets"
    )

    @property
    def row_and_seat(self) -> str:
        return f"{self.row}{self.seat}"

    @staticmethod
    def validate_seat_row(
            seat: str,
            seats_in_row: int,
            row: int,
            num_rows: int,
            error_to_raise: Type[Exception]
    ) -> None:
        # max possible literal of seat:
        max_seat_chr = chr(seats_in_row + 64)

        if not (("A" <= seat <= max_seat_chr) and (1 <= row <= num_rows)):
            raise error_to_raise(
                {
                    "seat": f"seat must be in range from A to {max_seat_chr}",
                    "row": f"row must be in range from 1 to {num_rows}",
                }
            )

    def clean(self) -> None:
        Ticket.validate_seat_row(
            self.seat,
            self.flight.aircraft.seats_in_row,
            self.row,
            self.flight.aircraft.rows,
            ValidationError,
        )

    class Meta:
        unique_together = ("seat", "row", "flight")
