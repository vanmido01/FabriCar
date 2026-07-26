from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Configuración administrativa de los clientes."""

    list_display = (
        "nombre",
        "documento",
        "tipo_cliente",
        "telefono",
        "correo",
        "estado",
    )

    search_fields = (
        "nombre",
        "documento",
        "telefono",
        "correo",
    )

    list_filter = (
        "tipo_cliente",
        "estado",
        "fecha_registro",
    )

    ordering = (
        "nombre",
    )

    readonly_fields = (
        "fecha_registro",
        "fecha_modificacion",
    )