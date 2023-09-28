from django.contrib import admin

from airport.models import (
    AircraftManufacturer,
    AircraftType,
    Aircraft,
    Airline,
    Airport,
    Crew,
    Flight,
    Route,
    Ticket,
    Order,
)

admin.site.register(AircraftManufacturer)
admin.site.register(AircraftType)
admin.site.register(Aircraft)
admin.site.register(Airline)
admin.site.register(Airport)
admin.site.register(Crew)
admin.site.register(Flight)
admin.site.register(Route)
admin.site.register(Ticket)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInline,)
