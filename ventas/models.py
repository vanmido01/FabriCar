from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from productos.models import Producto


class Venta(models.Model):
    """Representa una venta registrada en el sistema."""
    class TipoCliente(models.TextChoices):
        REGISTRADO = (
            "REGISTRADO",
            "Cliente registrado",
        )

        OCASIONAL = (
            "OCASIONAL",
            "Cliente ocasional",
        )
    class TipoComprobante(models.TextChoices):
        FACTURA = "FACTURA", "Factura"
        NOTA_VENTA = "NOTA_VENTA", "Nota de venta"
        RECIBO = "RECIBO", "Recibo"
        SIN_COMPROBANTE = (
            "SIN_COMPROBANTE",
            "Sin comprobante",
        )

    class FormaPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        QR = "QR", "Pago mediante QR"
        CREDITO = "CREDITO", "Crédito"

    class MetodoPagoInicial(models.TextChoices):
        EFECTIVO = (
            "EFECTIVO",
            "Efectivo",
        )

        TRANSFERENCIA = (
            "TRANSFERENCIA",
            "Transferencia",
        )

        QR = (
            "QR",
            "Pago mediante QR",
        )

        DEPOSITO = (
            "DEPOSITO",
            "Depósito bancario",
        )

    class EstadoVenta(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ANULADA = "ANULADA", "Anulada"

    tipo_cliente = models.CharField(
        max_length=20,
        choices=TipoCliente.choices,
        default=TipoCliente.REGISTRADO,
        db_index=True,
        verbose_name="Tipo de cliente",
    )

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
        null=True,
        blank=True,
        verbose_name="Cliente registrado",
    )

    nombre_cliente_ocasional = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Nombre del cliente ocasional",
    )

    documento_cliente_ocasional = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Documento del cliente ocasional",
    )

    telefono_cliente_ocasional = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono del cliente ocasional",
    )

    fecha_venta = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="Fecha de venta",
    )

    codigo_venta = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        unique=True,
        editable=False,
        verbose_name="Código interno de venta",
    )

    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TipoComprobante.choices,
        default=TipoComprobante.NOTA_VENTA,
        verbose_name="Tipo de comprobante",
    )

    numero_comprobante = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name=(
            "Número de factura o comprobante externo"
        ),
    )

    forma_pago = models.CharField(
        max_length=20,
        choices=FormaPago.choices,
        default=FormaPago.EFECTIVO,
        db_index=True,
        verbose_name="Forma de pago",
    )

    fecha_vencimiento_credito = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de vencimiento del crédito",
    )

    monto_pago_inicial = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(
                Decimal("0.00"),
            ),
        ],
        verbose_name="Monto del pago inicial",
    )

    metodo_pago_inicial = models.CharField(
        max_length=20,
        choices=MetodoPagoInicial.choices,
        blank=True,
        verbose_name="Método del pago inicial",
    )

    referencia_pago_inicial = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia del pago inicial",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoVenta.choices,
        default=EstadoVenta.BORRADOR,
        db_index=True,
        verbose_name="Estado",
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Total",
    )

    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_registradas",
        verbose_name="Registrado por",
    )

    usuario_confirmacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_confirmadas",
        verbose_name="Confirmado por",
    )

    fecha_confirmacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de confirmación",
    )

    usuario_anulacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventas_anuladas",
        verbose_name="Anulado por",
    )

    fecha_anulacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de anulación",
    )

    motivo_anulacion = models.TextField(
        blank=True,
        verbose_name="Motivo de anulación",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de modificación",
    )

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = [
            "-fecha_venta",
            "-id",
        ]

    @property
    def nombre_cliente_mostrado(self):
        """Devuelve el nombre correcto según el tipo de cliente."""

        if self.tipo_cliente == self.TipoCliente.OCASIONAL:
            return (
                self.nombre_cliente_ocasional
                or "Consumidor final"
            )

        if self.cliente:
            return self.cliente.nombre

        return "Cliente no definido"

    @property
    def documento_cliente_mostrado(self):
        """Devuelve el documento del cliente correspondiente."""

        if self.tipo_cliente == self.TipoCliente.OCASIONAL:
            return (
                self.documento_cliente_ocasional
                or ""
            )

        if self.cliente:
            return self.cliente.documento or ""

        return ""

    def save(self, *args, **kwargs):
        """Normaliza datos escritos manualmente."""

        self.numero_comprobante = (
            self.numero_comprobante or ""
        ).strip().upper()

        self.nombre_cliente_ocasional = (
            self.nombre_cliente_ocasional or ""
        ).strip()

        self.documento_cliente_ocasional = (
            self.documento_cliente_ocasional or ""
        ).strip().upper()

        self.telefono_cliente_ocasional = (
            self.telefono_cliente_ocasional or ""
        ).strip()

        self.referencia_pago_inicial = (
            self.referencia_pago_inicial or ""
        ).strip().upper()

        self.metodo_pago_inicial = (
            self.metodo_pago_inicial or ""
        ).strip().upper()

        super().save(*args, **kwargs)

    def actualizar_total(self):
        """Calcula el total utilizando los detalles registrados."""

        nuevo_total = sum(
            (
                detalle.subtotal
                for detalle in self.detalles.all()
            ),
            Decimal("0.00"),
        )

        self.total = nuevo_total

        self.save(
            update_fields=[
                "total",
                "fecha_modificacion",
            ]
        )

    def __str__(self):
        referencia = (
            self.codigo_venta
            or f"Venta N.º {self.id or 'nueva'}"
        )

        return (
            f"{referencia} - "
            f"{self.nombre_cliente_mostrado}"
        )


class SecuenciaVenta(models.Model):
    """
    Controla la numeración consecutiva de ventas por gestión.
    """

    gestion = models.PositiveIntegerField(
        unique=True,
        verbose_name="Gestión",
    )

    ultimo_numero = models.PositiveIntegerField(
        default=0,
        verbose_name="Último número utilizado",
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de modificación",
    )

    class Meta:
        verbose_name = "Secuencia de venta"
        verbose_name_plural = "Secuencias de venta"
        ordering = ["-gestion"]

    def __str__(self):
        return (
            f"Gestión {self.gestion} - "
            f"Último número: {self.ultimo_numero}"
        )

class DetalleVenta(models.Model):
    """Representa un producto incluido en una venta."""

    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Venta",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_venta",
        verbose_name="Producto",
    )

    cantidad = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
        verbose_name="Cantidad",
    )

    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Precio unitario",
    )

    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
        verbose_name="Subtotal",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Detalle de venta"
        verbose_name_plural = "Detalles de venta"
        ordering = ["id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "venta",
                    "producto",
                ],
                name="producto_unico_por_venta",
            )
        ]

    def save(self, *args, **kwargs):
        """Calcula el subtotal antes de guardar el detalle."""

        self.subtotal = (
            Decimal(self.cantidad)
            * self.precio_unitario
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.producto.codigo} - "
            f"{self.cantidad} unidad(es)"
        )