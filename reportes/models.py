from django.db import models


class ConfiguracionReportes(models.Model):
    """Configuración general utilizada en los reportes."""

    logo = models.ImageField(
        upload_to="reportes/logos/",
        blank=True,
        null=True,
        verbose_name="Logo de FABRI-CAR",
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Configuración de reportes"
        verbose_name_plural = "Configuración de reportes"

    def __str__(self):
        return "Configuración de reportes"