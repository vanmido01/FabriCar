from django.contrib import admin

from .models import DetalleVenta, Venta


class DetalleVentaInline(admin.TabularInline):
    """Permite registrar productos dentro de una venta."""

    model = DetalleVenta
    extra = 1

    fields = (
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )

    readonly_fields = (
        "subtotal",
    )


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """Configuración administrativa de las ventas."""

    list_display = (
        "id",
        "cliente",
        "fecha_venta",
        "tipo_comprobante",
        "numero_comprobante",
        "forma_pago",
        "estado",
        "total",
        "usuario_registro",
    )

    search_fields = (
        "numero_comprobante",
        "cliente__nombre",
        "cliente__documento",
    )

    list_filter = (
        "estado",
        "forma_pago",
        "tipo_comprobante",
        "fecha_venta",
    )

    ordering = (
        "-fecha_venta",
        "-id",
    )

    readonly_fields = (
        "total",
        "usuario_registro",
        "fecha_registro",
        "fecha_modificacion",
    )

    inlines = [
        DetalleVentaInline,
    ]

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """Registra el usuario responsable de la venta."""

        if not obj.usuario_registro:
            obj.usuario_registro = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def save_related(
        self,
        request,
        form,
        formsets,
        change,
    ):
        """Recalcula el total después de guardar los detalles."""

        super().save_related(
            request,
            form,
            formsets,
            change,
        )

        form.instance.actualizar_total()


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    """Configuración administrativa de los detalles de venta."""

    list_display = (
        "venta",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "fecha_registro",
    )

    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "venta__cliente__nombre",
        "venta__numero_comprobante",
    )

    list_filter = (
        "fecha_registro",
    )

    readonly_fields = (
        "subtotal",
        "fecha_registro",
    )