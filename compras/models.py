from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from productos.models import Producto
from proveedores.models import Proveedor

class Compra(models.Model):
    """Representa una compra realizada a un proveedor."""

    class TipoComprobante(models.TextChoices):
        FACTURA = "FACTURA", "Factura"
        NOTA_VENTA = "NOTA_VENTA", "Nota de venta"
        RECIBO = "RECIBO", "Recibo"
        OTRO = "OTRO", "Otro"

    class EstadoCompra(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        ANULADA = "ANULADA", "Anulada"

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="compras",
        verbose_name="Proveedor",
    )

    fecha_compra = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="Fecha de compra",
    )

    tipo_comprobante = models.CharField(
        max_length=20,
        choices=TipoComprobante.choices,
        default=TipoComprobante.FACTURA,
        verbose_name="Tipo de comprobante",
    )

    numero_comprobante = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        verbose_name="Número de comprobante",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoCompra.choices,
        default=EstadoCompra.BORRADOR,
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
        related_name="compras_registradas",
        verbose_name="Registrado por",
    )

    usuario_confirmacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="compras_confirmadas",
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
        related_name="compras_anuladas",
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
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

        ordering = [
            "-fecha_compra",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "proveedor",
                    "tipo_comprobante",
                    "numero_comprobante",
                ],
                condition=~models.Q(
                    numero_comprobante="",
                ),
                name="compra_comprobante_unico_proveedor_tipo",
            ),
        ]

    def save(self, *args, **kwargs):
        """
        Normaliza el número de comprobante antes de guardar.

        Evita diferencias por espacios o uso de minúsculas.
        """

        self.numero_comprobante = (
            self.numero_comprobante or ""
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
        return (
            f"Compra N.º {self.id} - "
            f"{self.proveedor.razon_social}"
        )


class DetalleCompra(models.Model):
    """Representa un producto incluido en una compra."""

    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Compra",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="detalles_compra",
        verbose_name="Producto",
    )

    cantidad = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
        verbose_name="Cantidad",
    )

    costo_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Costo unitario",
    )

    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Precio de venta",
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
        verbose_name = "Detalle de compra"
        verbose_name_plural = "Detalles de compra"
        ordering = ["id"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "compra",
                    "producto",
                ],
                name="producto_unico_por_compra",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    cantidad__gte=1,
                ),
                name="detalle_compra_cantidad_minima_uno",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    costo_unitario__gt=0,
                ),
                name="detalle_compra_costo_unitario_positivo",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    precio_venta__gt=0,
                ),
                name="detalle_compra_precio_venta_positivo",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    precio_venta__gte=models.F(
                        "costo_unitario",
                    )
                ),
                name=(
                    "detalle_compra_precio_venta_"
                    "mayor_igual_costo"
                ),
            ),
        ]

    def save(self, *args, **kwargs):
        """Calcula el subtotal antes de guardar el detalle."""

        self.subtotal = (
            Decimal(self.cantidad)
            * self.costo_unitario
        )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.producto.codigo} - "
            f"{self.cantidad} unidad(es)"
        )