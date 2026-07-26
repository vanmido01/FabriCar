from django.db import models


class Proveedor(models.Model):
    """Representa a un proveedor registrado en el sistema."""

    razon_social = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Nombre o razón social",
    )

    nit = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="NIT",
    )

    persona_contacto = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Persona de contacto",
    )

    telefono = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Teléfono",
    )

    correo = models.EmailField(
        blank=True,
        verbose_name="Correo electrónico",
    )

    direccion = models.TextField(
        blank=True,
        verbose_name="Dirección",
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
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["razon_social"]

    def __str__(self):
        return f"{self.nit} - {self.razon_social}"