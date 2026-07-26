from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Configuración del modelo Producto en el panel administrativo."""

    list_display = (
        "codigo",
        "nombre",
        "tipo",
        "marca",
        "precio_venta",
        "stock_actual",
        "estado",
    )

    search_fields = (
        "codigo",
        "nombre",
        "marca",
    )

    list_filter = (
        "tipo",
        "condicion",
        "estado",
    )

    ordering = (
        "nombre",
    )

    readonly_fields = (
        "fecha_registro",
        "fecha_modificacion",
    )

    list_per_page = 25