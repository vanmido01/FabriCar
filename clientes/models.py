from django.db import models


class Cliente(models.Model):
    """Representa a un cliente registrado en el sistema."""

    class TipoCliente(models.TextChoices):
        PARTICULAR = "PARTICULAR", "Particular"
        TALLER = "TALLER", "Taller mecánico"
        INSTITUCION = "INSTITUCION", "Institución"

    tipo_cliente = models.CharField(
        max_length=20,
        choices=TipoCliente.choices,
        default=TipoCliente.PARTICULAR,
        verbose_name="Tipo de cliente",
    )

    nombre = models.CharField(
        max_length=150,
        db_index=True,
        verbose_name="Nombre o razón social",
    )

    documento = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Documento de identidad o NIT",
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
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.documento} - {self.nombre}"