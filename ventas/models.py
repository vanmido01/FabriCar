from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from productos.models import Producto


class Venta(models.Model):
    """Representa una venta registrada en el sistema."""

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

    class EstadoVenta(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ANULADA = "ANULADA", "Anulada"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ventas",
        verbose_name="Cliente",
    )

    fecha_venta = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="Fecha de venta",
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
        verbose_name="Número de comprobante",
    )

    forma_pago = models.CharField(
        max_length=20,
        choices=FormaPago.choices,
        default=FormaPago.EFECTIVO,
        db_index=True,
        verbose_name="Forma de pago",
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
        return (
            f"Venta N.º {self.id} - "
            f"{self.cliente.nombre}"
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