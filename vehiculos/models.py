from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from productos.models import Producto


class Vehiculo(models.Model):
    """Representa un vehículo registrado en el sistema."""

    marca = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Marca",
    )

    modelo = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Modelo",
    )

    anio_desde = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(2100),
        ],
        verbose_name="Año desde",
    )

    anio_hasta = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(2100),
        ],
        verbose_name="Año hasta",
    )

    motor = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Motor",
    )

    estado = models.BooleanField(
        default=True,
        verbose_name="Activo",
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
        verbose_name = "Vehículo"
        verbose_name_plural = "Vehículos"
        ordering = ["marca", "modelo", "anio_desde"]

    def clean(self):
        """Valida que el rango de años sea correcto."""

        super().clean()

        if self.anio_hasta < self.anio_desde:
            raise ValidationError(
                {
                    "anio_hasta": (
                        "El año final no puede ser menor "
                        "que el año inicial."
                    )
                }
            )

    def __str__(self):
        rango_anios = f"{self.anio_desde}-{self.anio_hasta}"

        if self.motor:
            return (
                f"{self.marca} {self.modelo} "
                f"{rango_anios} - {self.motor}"
            )

        return f"{self.marca} {self.modelo} {rango_anios}"


class CompatibilidadProducto(models.Model):
    """Relaciona un producto con un vehículo compatible."""

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="compatibilidades",
        verbose_name="Producto",
    )

    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE,
        related_name="productos_compatibles",
        verbose_name="Vehículo",
    )

    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro",
    )

    class Meta:
        verbose_name = "Compatibilidad de producto"
        verbose_name_plural = "Compatibilidades de productos"
        ordering = [
            "vehiculo__marca",
            "vehiculo__modelo",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["producto", "vehiculo"],
                name="compatibilidad_producto_vehiculo_unica",
            )
        ]

    def __str__(self):
        return f"{self.producto.codigo} - {self.vehiculo}"