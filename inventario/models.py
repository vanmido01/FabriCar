from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from productos.models import Producto


class MovimientoInventario(models.Model):
    """Registra los ingresos, salidas y ajustes del inventario."""

    class TipoMovimiento(models.TextChoices):
        ENTRADA_COMPRA = (
            "ENTRADA_COMPRA",
            "Entrada por compra",
        )
        SALIDA_VENTA = (
            "SALIDA_VENTA",
            "Salida por venta",
        )
        AJUSTE_ENTRADA = (
            "AJUSTE_ENTRADA",
            "Ajuste de entrada",
        )
        AJUSTE_SALIDA = (
            "AJUSTE_SALIDA",
            "Ajuste de salida",
        )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
        verbose_name="Producto",
    )

    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TipoMovimiento.choices,
        db_index=True,
        verbose_name="Tipo de movimiento",
    )

    cantidad = models.PositiveIntegerField(
        validators=[
            MinValueValidator(1),
        ],
        verbose_name="Cantidad",
    )

    stock_anterior = models.PositiveIntegerField(
        verbose_name="Stock anterior",
    )

    stock_posterior = models.PositiveIntegerField(
        verbose_name="Stock posterior",
    )

    compra = models.ForeignKey(
        "compras.Compra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
        verbose_name="Compra relacionada",
    )

    venta = models.ForeignKey(
        "ventas.Venta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
        verbose_name="Venta relacionada",
    )

    motivo = models.CharField(
        max_length=200,
        verbose_name="Motivo",
    )

    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_inventario_registrados",
        verbose_name="Usuario responsable",
    )

    fecha_movimiento = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Fecha del movimiento",
    )

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = [
            "-fecha_movimiento",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.get_tipo_movimiento_display()} - "
            f"{self.producto.codigo} - "
            f"{self.cantidad} unidad(es)"
        )