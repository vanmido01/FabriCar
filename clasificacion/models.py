from django.conf import settings
from django.db import models

from productos.models import Producto


class ParametroClasificacion(models.Model):
    """Configuración utilizada para ejecutar una clasificación."""

    nombre = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre",
    )

    fecha_inicio = models.DateField(
        verbose_name="Fecha de inicio",
    )

    fecha_fin = models.DateField(
        verbose_name="Fecha de fin",
    )

    umbral_fast = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Umbral Fast",
    )

    umbral_slow = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Umbral Slow",
    )

    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
    )

    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parametros_clasificacion",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_modificacion = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-fecha_registro",
        ]
        verbose_name = "Parámetro de clasificación"
        verbose_name_plural = "Parámetros de clasificación"

    def __str__(self):
        return self.nombre


class ResultadoClasificacion(models.Model):

    class Categoria(models.TextChoices):
        FAST = "FAST", "Fast Moving"
        SLOW = "SLOW", "Slow Moving"
        NON = "NON", "Non Moving"

    parametro = models.ForeignKey(
        ParametroClasificacion,
        on_delete=models.CASCADE,
        related_name="resultados",
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="clasificaciones",
    )

    frecuencia = models.PositiveIntegerField()

    probabilidad = models.DecimalField(
        max_digits=8,
        decimal_places=6,
    )

    categoria = models.CharField(
        max_length=10,
        choices=Categoria.choices,
    )

    fecha_calculo = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Resultado de clasificación"
        verbose_name_plural = "Resultados de clasificación"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "parametro",
                    "producto",
                ],
                name="clasificacion_unica_producto_parametro",
            )
        ]

        ordering = [
            "categoria",
            "-probabilidad",
            "producto__nombre",
        ]

    def __str__(self):
        return (
            f"{self.producto.nombre} - "
            f"{self.get_categoria_display()}"
        )