from django.contrib import admin

from .models import CompatibilidadProducto, Vehiculo


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    """Configuración administrativa de los vehículos."""

    list_display = (
        "marca",
        "modelo",
        "anio_desde",
        "anio_hasta",
        "motor",
        "estado",
    )

    search_fields = (
        "marca",
        "modelo",
        "motor",
    )

    list_filter = (
        "estado",
        "marca",
    )

    ordering = (
        "marca",
        "modelo",
        "anio_desde",
    )


@admin.register(CompatibilidadProducto)
class CompatibilidadProductoAdmin(admin.ModelAdmin):
    """Configuración administrativa de compatibilidades."""

    list_display = (
        "producto",
        "vehiculo",
        "fecha_registro",
    )

    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "vehiculo__marca",
        "vehiculo__modelo",
    )

    list_filter = (
        "vehiculo__marca",
        "fecha_registro",
    )

    ordering = (
        "vehiculo__marca",
        "vehiculo__modelo",
    )