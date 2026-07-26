from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Producto(models.Model):
    """Representa un repuesto automotriz registrado en FABRI-CAR."""

    class TipoRepuesto(models.TextChoices):
        ORIGINAL = "ORIGINAL", "Original"
        ALTERNATIVO = "ALTERNATIVO", "Alternativo"
        ESTANDAR = "ESTANDAR", "Estándar"

    class CondicionProducto(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"
        USADO = "USADO", "Usado"

    codigo = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Código",
    )

    nombre = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Nombre",
    )

    descripcion = models.TextField(
        blank=True,
        verbose_name="Descripción",
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoRepuesto.choices,
        verbose_name="Tipo de repuesto",
    )

    condicion = models.CharField(
        max_length=10,
        choices=CondicionProducto.choices,
        verbose_name="Condición",
    )

    marca = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        verbose_name="Marca",
    )

    procedencia = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Procedencia",
    )

    precio_compra = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Precio de compra",
    )

    precio_venta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.00")),
        ],
        verbose_name="Precio de venta",
    )

    stock_actual = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock actual",
    )

    stock_minimo = models.PositiveIntegerField(
        default=0,
        verbose_name="Stock mínimo",
    )

    imagen = models.ImageField(
        upload_to="productos/",
        blank=True,
        null=True,
        verbose_name="Imagen",
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
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"