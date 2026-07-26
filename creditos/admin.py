from django.contrib import admin

from .models import Credito, PagoCredito


class PagoCreditoInline(admin.TabularInline):
    """Muestra los pagos registrados dentro de cada crédito."""

    model = PagoCredito
    extra = 0
    can_delete = False

    fields = (
        "fecha_pago",
        "monto",
        "metodo_pago",
        "referencia",
        "usuario_registro",
    )

    readonly_fields = (
        "fecha_pago",
        "monto",
        "metodo_pago",
        "referencia",
        "usuario_registro",
    )


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    """Configuración administrativa de las cuentas por cobrar."""

    list_display = (
        "id",
        "venta",
        "cliente",
        "fecha_inicio",
        "fecha_vencimiento",
        "monto_total",
        "saldo_pendiente",
        "estado",
        "credito_vencido",
        "usuario_registro",
    )

    search_fields = (
        "venta__numero_comprobante",
        "venta__cliente__nombre",
        "venta__cliente__documento",
    )

    list_filter = (
        "estado",
        "fecha_inicio",
        "fecha_vencimiento",
    )

    ordering = (
        "-fecha_inicio",
        "-id",
    )

    readonly_fields = (
        "usuario_registro",
        "fecha_registro",
        "fecha_modificacion",
    )

    inlines = [
        PagoCreditoInline,
    ]

    @admin.display(
        description="Cliente",
        ordering="venta__cliente__nombre",
    )
    def cliente(self, obj):
        """Muestra el cliente relacionado con la venta."""

        return obj.venta.cliente.nombre

    @admin.display(
        boolean=True,
        description="Vencido",
    )
    def credito_vencido(self, obj):
        """Indica si la cuenta por cobrar está vencida."""

        return obj.esta_vencido

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """Registra el usuario responsable del crédito."""

        if not obj.usuario_registro:
            obj.usuario_registro = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )


@admin.register(PagoCredito)
class PagoCreditoAdmin(admin.ModelAdmin):
    """Configuración administrativa de los pagos de créditos."""

    list_display = (
        "id",
        "credito",
        "cliente",
        "fecha_pago",
        "monto",
        "metodo_pago",
        "referencia",
        "usuario_registro",
    )

    search_fields = (
        "credito__venta__numero_comprobante",
        "credito__venta__cliente__nombre",
        "referencia",
    )

    list_filter = (
        "metodo_pago",
        "fecha_pago",
    )

    ordering = (
        "-fecha_pago",
        "-id",
    )

    readonly_fields = (
        "usuario_registro",
        "fecha_registro",
    )

    @admin.display(
        description="Cliente",
        ordering="credito__venta__cliente__nombre",
    )
    def cliente(self, obj):
        """Muestra el cliente propietario del crédito."""

        return obj.credito.venta.cliente.nombre

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        """Registra el usuario responsable del pago."""

        if not obj.usuario_registro:
            obj.usuario_registro = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )