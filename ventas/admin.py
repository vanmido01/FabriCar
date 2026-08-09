from django.contrib import admin

from .models import (
    DetalleVenta,
    SecuenciaVenta,
    Venta,
)


class DetalleVentaInline(admin.TabularInline):
    """
    Muestra los productos de la venta como historial.

    No permite agregar, modificar ni eliminar productos
    desde el panel administrativo.
    """

    model = DetalleVenta
    extra = 0
    can_delete = False
    show_change_link = False

    fields = (
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "fecha_registro",
    )

    readonly_fields = fields

    def has_add_permission(
        self,
        request,
        obj=None,
    ):
        """Impide agregar productos desde el administrador."""

        return False

    def has_change_permission(
        self,
        request,
        obj=None,
    ):
        """
        Permite visualizar el inline, pero todos
        sus campos permanecen bloqueados.
        """

        return True

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """Impide eliminar productos desde el administrador."""

        return False


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """
    Presenta las ventas como historial protegido.

    Las operaciones comerciales deben realizarse desde
    las vistas normales del módulo Ventas.
    """

    list_display = (
        "codigo_mostrado",
        "fecha_venta",
        "cliente_mostrado",
        "tipo_cliente",
        "forma_pago",
        "estado",
        "total",
        "usuario_registro",
        "usuario_confirmacion",
    )

    search_fields = (
        "codigo_venta",
        "numero_comprobante",
        "cliente__nombre",
        "cliente__documento",
        "nombre_cliente_ocasional",
        "documento_cliente_ocasional",
        "telefono_cliente_ocasional",
        "usuario_registro__username",
        "usuario_confirmacion__username",
        "usuario_anulacion__username",
    )

    list_filter = (
        "estado",
        "tipo_cliente",
        "forma_pago",
        "tipo_comprobante",
        "fecha_venta",
    )

    ordering = (
        "-fecha_venta",
        "-id",
    )

    list_select_related = (
        "cliente",
        "usuario_registro",
        "usuario_confirmacion",
        "usuario_anulacion",
    )

    fieldsets = (
        (
            "Identificación de la venta",
            {
                "fields": (
                    "codigo_venta",
                    "estado",
                    "fecha_venta",
                )
            },
        ),
        (
            "Información del cliente",
            {
                "fields": (
                    "tipo_cliente",
                    "cliente",
                    "nombre_cliente_ocasional",
                    "documento_cliente_ocasional",
                    "telefono_cliente_ocasional",
                )
            },
        ),
        (
            "Información comercial",
            {
                "fields": (
                    "tipo_comprobante",
                    "numero_comprobante",
                    "forma_pago",
                    "total",
                    "observaciones",
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

    readonly_fields = (
        "codigo_venta",
        "estado",
        "fecha_venta",
        "tipo_cliente",
        "cliente",
        "nombre_cliente_ocasional",
        "documento_cliente_ocasional",
        "telefono_cliente_ocasional",
        "tipo_comprobante",
        "numero_comprobante",
        "forma_pago",
        "total",
        "observaciones",
        "usuario_registro",
        "fecha_registro",
        "usuario_confirmacion",
        "fecha_confirmacion",
        "usuario_anulacion",
        "fecha_anulacion",
        "motivo_anulacion",
        "fecha_modificacion",
    )

    inlines = [
        DetalleVentaInline,
    ]

    @admin.display(
        description="Código de venta",
        ordering="codigo_venta",
    )
    def codigo_mostrado(self, obj):
        """Muestra el código definitivo o el número del borrador."""

        if obj.codigo_venta:
            return obj.codigo_venta

        return f"Borrador N.º {obj.id}"

    @admin.display(
        description="Cliente",
    )
    def cliente_mostrado(self, obj):
        """Muestra correctamente clientes registrados u ocasionales."""

        return obj.nombre_cliente_mostrado

    def get_queryset(self, request):
        """Optimiza las relaciones utilizadas en el listado."""

        return (
            super()
            .get_queryset(request)
            .select_related(
                "cliente",
                "usuario_registro",
                "usuario_confirmacion",
                "usuario_anulacion",
            )
        )

    def has_add_permission(self, request):
        """
        Impide crear ventas desde el administrador.

        Deben registrarse desde el módulo comercial.
        """

        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """
        Impide eliminar ventas.

        Las operaciones incorrectas deben anularse para
        conservar el historial y la trazabilidad.
        """

        return False

    def get_actions(self, request):
        """Retira la eliminación masiva."""

        acciones = super().get_actions(request)
        acciones.pop(
            "delete_selected",
            None,
        )

        return acciones


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    """Presenta los detalles de venta como historial protegido."""

    list_display = (
        "venta",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "fecha_registro",
    )

    search_fields = (
        "venta__codigo_venta",
        "venta__numero_comprobante",
        "venta__cliente__nombre",
        "venta__nombre_cliente_ocasional",
        "producto__codigo",
        "producto__nombre",
    )

    list_filter = (
        "venta__estado",
        "fecha_registro",
    )

    ordering = (
        "-fecha_registro",
        "-id",
    )

    list_select_related = (
        "venta",
        "producto",
    )

    fields = (
        "venta",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "fecha_registro",
    )

    readonly_fields = fields

    def has_add_permission(self, request):
        """Impide crear detalles directamente."""

        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """Impide eliminar detalles directamente."""

        return False

    def get_actions(self, request):
        """Retira la eliminación masiva."""

        acciones = super().get_actions(request)
        acciones.pop(
            "delete_selected",
            None,
        )

        return acciones


@admin.register(SecuenciaVenta)
class SecuenciaVentaAdmin(admin.ModelAdmin):
    """
    Muestra el consecutivo utilizado por cada gestión.

    La secuencia no debe modificarse manualmente porque
    controla los códigos VTA-AAAA-000000.
    """

    list_display = (
        "gestion",
        "ultimo_numero",
        "fecha_modificacion",
    )

    ordering = (
        "-gestion",
    )

    readonly_fields = (
        "gestion",
        "ultimo_numero",
        "fecha_modificacion",
    )

    def has_add_permission(self, request):
        """La secuencia se crea automáticamente al confirmar."""

        return False

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """Impide eliminar una secuencia ya utilizada."""

        return False

    def get_actions(self, request):
        """Retira la eliminación masiva."""

        acciones = super().get_actions(request)
        acciones.pop(
            "delete_selected",
            None,
        )

        return acciones