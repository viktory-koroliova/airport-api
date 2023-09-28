from django.db import transaction
from rest_framework import serializers

from airport.models import (
    Airline,
    Crew,
    Aircraft,
    AircraftType,
    AircraftManufacturer,
    Airport,
    Route,
    Flight,
    Ticket,
    Order
)


class AircraftManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AircraftManufacturer
        fields = ("id", "name", "country")


class AircraftTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AircraftType
        fields = ("id", "name", "manufacturer")


class AircraftTypeListSerializer(AircraftTypeSerializer):
    manufacturer = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name"
    )


class AircraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aircraft
        fields = (
            "id",
            "registration",
            "production_year",
            "rows",
            "seats_in_row",
            "aircraft_type"
        )


class AircraftListSerializer(serializers.ModelSerializer):
    aircraft_type = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name"
    )

    class Meta:
        model = Aircraft
        fields = (
            "id",
            "registration",
            "age",
            "aircraft_type",
            "capacity",
        )


class AircraftDetailSerializer(AircraftListSerializer):

    class Meta:
        model = Aircraft
        fields = (
            "id",
            "registration",
            "production_year",
            "rows",
            "seats_in_row",
            "capacity",
            "aircraft_type"
        )


class AircraftImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aircraft
        fields = ("id", "image")


class AirlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airline
        fields = (
            "id",
            "name",
            "iata_code",
            "icao_code",
            "callsign",
            "country",
            "notes"
        )


class AirlineListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airline
        fields = ("id", "name", "iata_code", "country")


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = (
            "id",
            "name",
            "nearest_city",
            "iata_code",
            "icao_code",
            "info"
        )


class AirportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "nearest_city", "iata_code")


class CrewSerializer(serializers.ModelSerializer):

    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "license_number")


class CrewListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "full_name")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "route_name")


class RouteDetailSerializer(RouteSerializer):
    source = serializers.StringRelatedField()
    destination = serializers.StringRelatedField()


class FlightSerializer(serializers.ModelSerializer):

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "airline",
            "route",
            "aircraft",
            "departure_time",
            "arrival_time",
            "crew",
            "status"
        )


class FlightListSerializer(serializers.ModelSerializer):
    airline = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="name"
    )
    route = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="route_name"
    )
    aircraft = serializers.CharField(
        read_only=True,
        source="aircraft.name"
    )
    seats_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "airline",
            "route",
            "seats_left",
            "aircraft",
            "departure_time",
            "arrival_time",
            "status"
        )


class FlightDetailSerializer(FlightListSerializer):
    aircraft = AircraftListSerializer(many=False, read_only=True)
    crew = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="full_name"
    )
    taken_seats = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        source="tickets",
        slug_field="row_and_seat"
    )

    class Meta:
        model = Flight
        fields = (
            "id",
            "flight_number",
            "airline",
            "route",
            "aircraft",
            "departure_time",
            "arrival_time",
            "taken_seats",
            "crew",
            "status"
        )


class TicketSerializer(serializers.ModelSerializer):

    def validate(self, attrs: dict) -> dict:
        data = super(TicketSerializer, self).validate(attrs)
        Ticket.validate_seat_row(
            attrs["seat"],
            attrs["flight"].aircraft.seats_in_row,
            attrs["row"],
            attrs["flight"].aircraft.rows,
            serializers.ValidationError
        )
        return data

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight")


class TicketListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat")


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=False, allow_empty=False)

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def validate(self, data: dict) -> dict:
        tickets = data["tickets"]

        # It is not allowed to have tickets for different flight in an order
        flights = {ticket["flight"].id for ticket in tickets}
        if len(flights) > 1:
            raise serializers.ValidationError(
                "All tickets in an order must refer to the same flight."
            )

        return data

    def create(self, validated_data: dict) -> Order:
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
            return order


class OrderListSerializer(serializers.ModelSerializer):
    route = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    number_of_tickets = serializers.IntegerField()

    class Meta:
        model = Order
        fields = ("id", "route", "date", "number_of_tickets", "status")

    def get_route(self, obj: Order) -> str:
        return str(obj.tickets.first().flight.route)

    def get_date(self, obj: Order) -> str:
        return obj.tickets.first().flight.departure_time.strftime("%d %b, %Y")


class OrderDetailSerializer(OrderListSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
    departure_time = serializers.SerializerMethodField()
    airline = serializers.SerializerMethodField()

    def get_airline(self, obj: Order) -> str:
        return obj.tickets.first().flight.airline.name

    def get_departure_time(self, obj: Order) -> str:
        return (
            obj.tickets.first().flight.
            departure_time.strftime("%d %b, %Y  %H:%M")
        )

    class Meta:
        model = Order
        fields = (
            "id",
            "route",
            "airline",
            "departure_time",
            "tickets",
            "created_at",
            "status"
        )
