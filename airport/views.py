from typing import Type, Optional, Any

from django.db.models import F, Count, QuerySet
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer

from airport import serializers
from airport.models import (
    AircraftManufacturer,
    AircraftType,
    Aircraft,
    Airline,
    Airport,
    Crew,
    Flight,
    Route,
    Order,
)


def _params_to_int(qs: str) -> list[int]:
    return [int(str_id) for str_id in qs.split(",")]


class AircraftManufacturerView(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = AircraftManufacturer.objects.all()
    serializer_class = serializers.AircraftManufacturerSerializer


class AircraftTypeViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = AircraftType.objects.all()
    serializer_class = serializers.AircraftTypeSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        if self.action == "list":
            queryset = queryset.select_related("manufacturer")
        return queryset

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.AircraftTypeListSerializer
        return serializers.AircraftTypeSerializer


class AircraftViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Aircraft.objects.all()

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.AircraftListSerializer
        if self.action == "retrieve":
            return serializers.AircraftDetailSerializer
        if self.action == "upload_image":
            return serializers.AircraftImageSerializer
        return serializers.AircraftSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        aircraft_types = self.request.query_params.get("types")

        if self.action == "list":
            queryset = queryset.select_related("aircraft_type")
        if aircraft_types is not None:
            aircraft_types_ids = _params_to_int(aircraft_types)
            queryset = queryset.filter(aircraft_type__in=aircraft_types_ids)
        return queryset

    @action(methods=["POST"], detail=True, url_path="upload-image")
    def upload_image(
            self,
            request: Request,
            pk: Optional[int] = None
    ) -> Response:
        aircraft = self.get_object()
        serializer = self.get_serializer(aircraft, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "types",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by aircraft_type id. Ex: ?types=1,2",
                required=False,
            )
        ]
    )
    def list(
            self,
            request: Request,
            *args: tuple[Any],
            **kwargs: dict[str, Any]
    ) -> Response:
        return super().list(request, *args, **kwargs)


class AirlineViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Airline.objects.all()
    lookup_field = "iata_code"

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.AirlineListSerializer
        return serializers.AirlineSerializer


class AirportViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Airport.objects.all()
    lookup_field = "iata_code"

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.AirportListSerializer
        return serializers.AirportSerializer


class CrewViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Crew.objects.all()

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.CrewListSerializer
        return serializers.CrewSerializer


class FlightViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = (
        Flight.objects.all()
        .annotate(
            seats_left=(
                F("aircraft__rows") * F("aircraft__seats_in_row")
                - Count("tickets")
            )
        )
        .order_by("departure_time")
    )

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.FlightListSerializer
        if self.action == "retrieve":
            return serializers.FlightDetailSerializer
        return serializers.FlightSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        routes = self.request.query_params.get("routes")
        crew = self.request.query_params.get("crew")
        statuses = self.request.query_params.get("statuses")

        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related(
                "airline",
                "route__source",
                "route__destination",
                "aircraft__aircraft_type",
            )
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("crew")

        if routes is not None:
            routes_ids = _params_to_int(routes)
            queryset = queryset.filter(route__in=routes_ids)

        if crew is not None:
            crew_ids = _params_to_int(crew)
            queryset = queryset.filter(crew__in=crew_ids)

        if statuses is not None:
            status_list = statuses.split(",")
            queryset = queryset.filter(status__in=status_list)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "routes",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by route id. Ex: ?routes=1,2",
            ),
            OpenApiParameter(
                "crew",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by crew id. Ex: ?crew=1,2",
            ),
            OpenApiParameter(
                "statuses",
                type={"type": "list", "items": {"type": "string"}},
                description="Filter by status. Ex: ?status=on_time,delayed",
            ),
        ]
    )
    def list(
            self,
            request: Request,
            *args: tuple[Any],
            **kwargs: dict[str, Any]
    ) -> Response:
        return super().list(request, *args, **kwargs)


class RouteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Route.objects.all()

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.RouteListSerializer
        if self.action == "retrieve":
            return serializers.RouteDetailSerializer
        return serializers.RouteSerializer

    def get_queryset(self) -> QuerySet:
        queryset = self.queryset

        sources = self.request.query_params.get("sources")
        destinations = self.request.query_params.get("destinations")

        if self.action in ("list", "retrieve"):
            queryset = queryset.select_related("source", "destination")

        if sources:
            source_list = sources.upper().split(",")
            queryset = queryset.filter(source__iata_code__in=source_list)

        if destinations:
            destination_list = destinations.upper().split(",")
            queryset = queryset.filter(
                destination__iata_code__in=destination_list
            )

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "sources",
                type={"type": "list", "items": {"type": "string"}},
                description="Filter by departure airport IATA code. "
                            "Ex: sources=jfk,kbp",
            ),
            OpenApiParameter(
                "destinations",
                type={"type": "list", "items": {"type": "string"}},
                description="Filter by arrival airport IATA code. "
                            "Ex: ?destinations=jfk,kbp",
            ),
        ],
    )
    def list(
            self,
            request: Request,
            *args: tuple[Any],
            **kwargs: dict[str, Any]
    ) -> Response:
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Order.objects.all().annotate(number_of_tickets=Count("tickets"))
    permission_classes = (IsAuthenticated,)

    def get_queryset(self) -> QuerySet:
        return self.queryset.filter(user=self.request.user)

    def get_serializer_class(self) -> Type[Serializer]:
        if self.action == "list":
            return serializers.OrderListSerializer
        if self.action == "retrieve":
            return serializers.OrderDetailSerializer
        return serializers.OrderSerializer

    def perform_create(self, serializer: Serializer) -> None:
        serializer.save(user=self.request.user)
