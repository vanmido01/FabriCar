from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from ventas.models import Venta, DetalleVenta

from .models import ResultadoClasificacion


@transaction.atomic
def ejecutar_clasificacion(parametro):

    detalles = (
        DetalleVenta.objects
        .filter(
            venta__estado=Venta.EstadoVenta.CONFIRMADA,
            venta__fecha_venta__range=(
                parametro.fecha_inicio,
                parametro.fecha_fin,
            ),
        )
        .values(
            "producto",
        )
        .annotate(
            frecuencia=Sum("cantidad"),
        )
        .order_by()
    )

    frecuencia_total = sum(
        fila["frecuencia"]
        for fila in detalles
    )

    # Eliminar los resultados anteriores antes de recalcular.
    ResultadoClasificacion.objects.filter(
        parametro=parametro,
    ).delete()

    if frecuencia_total == 0:
        return {
            "productos": 0,
            "fast": 0,
            "slow": 0,
            "non": 0,
        }

    fast = 0
    slow = 0
    non = 0

    for fila in detalles:

        probabilidad = (
            Decimal(fila["frecuencia"])
            / Decimal(frecuencia_total)
        )

        if probabilidad >= parametro.umbral_fast:

            categoria = ResultadoClasificacion.Categoria.FAST
            fast += 1

        elif probabilidad >= parametro.umbral_slow:

            categoria = ResultadoClasificacion.Categoria.SLOW
            slow += 1

        else:

            categoria = ResultadoClasificacion.Categoria.NON
            non += 1

        ResultadoClasificacion.objects.create(
            parametro=parametro,
            producto_id=fila["producto"],
            frecuencia=fila["frecuencia"],
            probabilidad=probabilidad,
            categoria=categoria,
        )

    return {
        "productos": len(detalles),
        "fast": fast,
        "slow": slow,
        "non": non,
    }