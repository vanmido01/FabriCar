from django.contrib import admin

from .models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    """Configuración administrativa del historial de inventario."""

    list_display = (
        "fecha_movimiento",
        "producto",
        "tipo_movimiento",
        "cantidad",
        "stock_anterior",
        "stock_posterior",
        "compra",
        "usuario",
    )

    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "motivo",
        "observaciones",
        "compra__numero_comprobante",
        "usuario__username",
    )

    list_filter = (
        "tipo_movimiento",
        "fecha_movimiento",
    )

    ordering = (
        "-fecha_movimiento",
        "-id",
    )

    readonly_fields = (
        "producto",
        "tipo_movimiento",
        "cantidad",
        "stock_anterior",
        "stock_posterior",
        "compra",
        "motivo",
        "observaciones",
        "usuario",
        "fecha_movimiento",
    )

    def has_add_permission(self, request):
        """Impide crear movimientos manualmente desde administración."""

        return False

    def has_change_permission(self, request, obj=None):
        """Permite consultar, pero no modificar movimientos."""

        return request.user.is_active and request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        """Impide eliminar el historial de inventario."""

        return False