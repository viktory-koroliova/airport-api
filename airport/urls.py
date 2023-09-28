from rest_framework import routers

from airport.views import (
    AircraftManufacturerView,
    AircraftTypeViewSet,
    AircraftViewSet,
    AirlineViewSet,
    AirportViewSet,
    CrewViewSet,
    FlightViewSet,
    RouteViewSet,
    OrderViewSet,
)

router = routers.DefaultRouter()
router.register("manufacturers", AircraftManufacturerView)
router.register("aircraft_types", AircraftTypeViewSet)
router.register("aircraft", AircraftViewSet)
router.register("airlines", AirlineViewSet)
router.register("airports", AirportViewSet)
router.register("crew", CrewViewSet)
router.register("flights", FlightViewSet)
router.register("routes", RouteViewSet)
router.register("orders", OrderViewSet)

urlpatterns = router.urls

app_name = "airport"
