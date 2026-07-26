from django.contrib import admin

from .models import Compra, DetalleCompra


class DetalleCompraInline(admin.TabularInline):
    """Permite registrar los productos dentro de una compra."""

    model = DetalleCompra
    extra = 1

    fields = (
        "producto",
        "cantidad",
        "costo_unitario",
        "subtotal",
    )

    readonly_fields = (
        "subtotal",
    )


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    """Configuración administrativa de las compras."""

    list_display = (
        "id",
        "proveedor",
        "fecha_compra",
        "tipo_comprobante",
        "numero_comprobante",
        "estado",
        "total",
        "usuario_registro",
    )

    search_fields = (
        "numero_comprobante",
        "proveedor__razon_social",
        "proveedor__nit",
    )

    list_filter = (
        "estado",
        "tipo_comprobante",
        "fecha_compra",
    )

    ordering = (
        "-fecha_compra",
        "-id",
    )

    readonly_fields = (
        "total",
        "usuario_registro",
        "fecha_registro",
        "fecha_modificacion",
    )

    inlines = [
        DetalleCompraInline,
    ]

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """Guarda el usuario que registra la compra."""

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


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    """Configuración administrativa de los detalles de compra."""

    list_display = (
        "compra",
        "producto",
        "cantidad",
        "costo_unitario",
        "subtotal",
        "fecha_registro",
    )

    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "compra__proveedor__razon_social",
    )

    list_filter = (
        "fecha_registro",
    )

    readonly_fields = (
        "subtotal",
        "fecha_registro",
    )