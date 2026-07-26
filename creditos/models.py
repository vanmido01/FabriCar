from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from ventas.models import Venta


def fecha_vencimiento_predeterminada():
    """Establece un vencimiento inicial de treinta días."""

    return timezone.localdate() + timedelta(days=30)


class Credito(models.Model):
    """Representa una cuenta por cobrar originada por una venta."""

    class EstadoCredito(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PARCIAL = "PARCIAL", "Pago parcial"
        PAGADO = "PAGADO", "Pagado"
        ANULADO = "ANULADO", "Anulado"

    venta = models.OneToOneField(
        Venta,
        on_delete=models.PROTECT,
        related_name="credito",
        verbose_name="Venta relacionada",
    )

    fecha_inicio = models.DateField(
        default=timezone.localdate,
        verbose_name="Fecha de inicio",
    )

    fecha_vencimiento = models.DateField(
        default=fecha_vencimiento_predeterminada,
        db_index=True,
        verbose_name="Fecha de vencimiento",
    )

    monto_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Monto total",
    )

    saldo_pendiente = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Saldo pendiente",
    )

    estado = models.CharField(
        max_length=20,
        choices=EstadoCredito.choices,
        default=EstadoCredito.PENDIENTE,
        db_index=True,
        verbose_name="Estado",
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
        related_name="creditos_registrados",
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
        verbose_name = "Crédito"
        verbose_name_plural = "Créditos"
        ordering = [
            "-fecha_inicio",
            "-id",
        ]

    def clean(self):
        """Valida que el crédito corresponda a una venta a crédito."""

        super().clean()

        if (
            self.venta_id
            and self.venta.forma_pago
            != Venta.FormaPago.CREDITO
        ):
            raise ValidationError(
                {
                    "venta": (
                        "La venta seleccionada no tiene como "
                        "forma de pago Crédito."
                    )
                }
            )

        if self.saldo_pendiente > self.monto_total:
            raise ValidationError(
                {
                    "saldo_pendiente": (
                        "El saldo pendiente no puede superar "
                        "el monto total del crédito."
                    )
                }
            )

    @property
    def esta_vencido(self):
        """Indica si el crédito tiene saldo después del vencimiento."""

        return (
            self.estado
            not in [
                self.EstadoCredito.PAGADO,
                self.EstadoCredito.ANULADO,
            ]
            and self.saldo_pendiente > 0
            and self.fecha_vencimiento
            < timezone.localdate()
        )

    def actualizar_saldo(self):
        """Recalcula el saldo y el estado según los pagos registrados."""

        total_pagado = (
            self.pagos.aggregate(
                total=Sum("monto")
            )["total"]
            or Decimal("0.00")
        )

        nuevo_saldo = self.monto_total - total_pagado

        if nuevo_saldo < Decimal("0.00"):
            nuevo_saldo = Decimal("0.00")

        self.saldo_pendiente = nuevo_saldo

        if self.estado != self.EstadoCredito.ANULADO:
            if nuevo_saldo == Decimal("0.00"):
                self.estado = self.EstadoCredito.PAGADO
            elif total_pagado > Decimal("0.00"):
                self.estado = self.EstadoCredito.PARCIAL
            else:
                self.estado = self.EstadoCredito.PENDIENTE

        self.save(
            update_fields=[
                "saldo_pendiente",
                "estado",
                "fecha_modificacion",
            ]
        )

    def __str__(self):
        return (
            f"Crédito N.º {self.id} - "
            f"Venta N.º {self.venta_id}"
        )


class PagoCredito(models.Model):
    """Representa un pago realizado sobre una cuenta por cobrar."""

    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        QR = "QR", "Pago mediante QR"
        DEPOSITO = "DEPOSITO", "Depósito bancario"

    credito = models.ForeignKey(
        Credito,
        on_delete=models.CASCADE,
        related_name="pagos",
        verbose_name="Crédito",
    )

    fecha_pago = models.DateField(
        default=timezone.localdate,
        db_index=True,
        verbose_name="Fecha de pago",
    )

    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Monto pagado",
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices,
        default=MetodoPago.EFECTIVO,
        verbose_name="Método de pago",
    )

    referencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Referencia del pago",
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
        related_name="pagos_credito_registrados",
        verbose_name="Registrado por",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Pago de crédito"
        verbose_name_plural = "Pagos de créditos"
        ordering = [
            "-fecha_pago",
            "-id",
        ]

    def save(self, *args, **kwargs):
        """Guarda el pago y actualiza el saldo del crédito."""

        super().save(*args, **kwargs)
        self.credito.actualizar_saldo()

    def delete(self, *args, **kwargs):
        """Elimina el pago y vuelve a calcular el saldo."""

        credito = self.credito
        resultado = super().delete(*args, **kwargs)
        credito.actualizar_saldo()

        return resultado

    def __str__(self):
        return (
            f"Pago de Bs {self.monto} - "
            f"Crédito N.º {self.credito_id}"
        )