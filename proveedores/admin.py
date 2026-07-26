from django.contrib import admin

from .models import Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    """Configuración administrativa de los proveedores."""

    list_display = (
        "razon_social",
        "nit",
        "persona_contacto",
        "telefono",
        "correo",
        "estado",
    )

    search_fields = (
        "razon_social",
        "nit",
        "persona_contacto",
        "telefono",
        "correo",
    )

    list_filter = (
        "estado",
        "fecha_registro",
    )

    ordering = (
        "razon_social",
    )

    readonly_fields = (
        "fecha_registro",
        "fecha_modificacion",
    )