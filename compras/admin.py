from django.contrib import admin

from .models import Compra, DetalleCompra


class DetalleCompraInline(admin.TabularInline):
    """Administra los productos dentro de una compra en borrador."""

    model = DetalleCompra
    extra = 1

    fields = (
        "producto",
        "cantidad",
        "costo_unitario",
        "precio_venta",
        "subtotal",
    )

    readonly_fields = (
        "subtotal",
    )

    def get_readonly_fields(self, request, obj=None):
        """
        Bloquea todos los detalles cuando la compra
        ya fue confirmada o anulada.
        """

        if (
            obj
            and obj.estado != Compra.EstadoCompra.BORRADOR
        ):
            return self.fields

        return self.readonly_fields

    def get_extra(self, request, obj=None, **kwargs):
        """Oculta filas nuevas en compras bloqueadas."""

        if (
            obj
            and obj.estado != Compra.EstadoCompra.BORRADOR
        ):
            return 0

        return 1

    def has_add_permission(self, request, obj=None):
        """Solo permite agregar productos a compras en borrador."""

        if obj is None:
            return True

        return obj.estado == Compra.EstadoCompra.BORRADOR

    def has_delete_permission(self, request, obj=None):
        """Solo permite quitar productos de compras en borrador."""

        if obj is None:
            return True

        return obj.estado == Compra.EstadoCompra.BORRADOR


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    """Administración protegida de las compras."""

    list_display = (
        "id",
        "proveedor",
        "fecha_compra",
        "tipo_comprobante",
        "numero_comprobante",
        "estado",
        "total",
        "usuario_registro",
        "usuario_confirmacion",
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

    fieldsets = (
        (
            "Información general",
            {
                "fields": (
                    "proveedor",
                    "fecha_compra",
                    "tipo_comprobante",
                    "numero_comprobante",
                    "observaciones",
                )
            },
        ),
        (
            "Control de la compra",
            {
                "fields": (
                    "estado",
                    "total",
                )
            },
        ),
        (
            "Auditoría",
            {
                "fields": (
                    "usuario_registro",
                    "fecha_registro",
                    "usuario_confirmacion",
                    "fecha_confirmacion",
                    "usuario_anulacion",
                    "fecha_anulacion",
                    "motivo_anulacion",
                    "fecha_modificacion",
                )
            },
        ),
    )

    inlines = [
        DetalleCompraInline,
    ]

    def get_queryset(self, request):
        """Carga las relaciones utilizadas en el listado."""

        return (
            super()
            .get_queryset(request)
            .select_related(
                "proveedor",
                "usuario_registro",
                "usuario_confirmacion",
                "usuario_anulacion",
            )
        )

    def get_readonly_fields(self, request, obj=None):
        """
        El estado y la auditoría nunca se modifican manualmente.

        Cuando la compra está confirmada o anulada,
        también bloquea toda la información comercial.
        """

        campos_controlados = (
            "estado",
            "total",
            "usuario_registro",
            "fecha_registro",
            "usuario_confirmacion",
            "fecha_confirmacion",
            "usuario_anulacion",
            "fecha_anulacion",
            "motivo_anulacion",
            "fecha_modificacion",
        )

        if (
            obj
            and obj.estado != Compra.EstadoCompra.BORRADOR
        ):
            return campos_controlados + (
                "proveedor",
                "fecha_compra",
                "tipo_comprobante",
                "numero_comprobante",
                "observaciones",
            )

        return campos_controlados

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """
        Toda compra creada desde el administrador
        comienza obligatoriamente como borrador.
        """

        if not change:
            obj.usuario_registro = request.user
            obj.estado = Compra.EstadoCompra.BORRADOR

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
        """Recalcula el total únicamente en compras en borrador."""

        super().save_related(
            request,
            form,
            formsets,
            change,
        )

        compra = form.instance

        if compra.estado == Compra.EstadoCompra.BORRADOR:
            compra.actualizar_total()

    def has_delete_permission(self, request, obj=None):
        """
        Solo permite eliminar individualmente una compra
        que todavía permanece en borrador.
        """

        if obj is None:
            return False

        return obj.estado == Compra.EstadoCompra.BORRADOR

    def get_actions(self, request):
        """Retira la eliminación masiva de compras."""

        acciones = super().get_actions(request)
        acciones.pop("delete_selected", None)

        return acciones


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    """
    Presenta los detalles como historial de solo lectura.

    Las modificaciones deben realizarse desde la compra
    mientras permanezca en borrador.
    """

    list_display = (
        "compra",
        "producto",
        "cantidad",
        "costo_unitario",
        "precio_venta",
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
        "compra__estado",
    )

    readonly_fields = (
        "compra",
        "producto",
        "cantidad",
        "costo_unitario",
        "precio_venta",
        "subtotal",
        "fecha_registro",
    )

    def has_add_permission(self, request):
        """Impide crear detalles fuera de una compra."""

        return False

    def has_change_permission(self, request, obj=None):
        """Impide modificar detalles directamente."""

        return False

    def has_delete_permission(self, request, obj=None):
        """Impide eliminar detalles directamente."""

        return False