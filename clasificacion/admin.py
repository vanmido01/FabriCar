from django.contrib import admin

from .models import (
    ParametroClasificacion,
    ResultadoClasificacion,
)


@admin.register(ParametroClasificacion)
class ParametroClasificacionAdmin(admin.ModelAdmin):

    list_display = (
        "nombre",
        "fecha_inicio",
        "fecha_fin",
        "umbral_fast",
        "umbral_slow",
        "activo",
    )

    list_filter = (
        "activo",
    )

    search_fields = (
        "nombre",
    )


@admin.register(ResultadoClasificacion)
class ResultadoClasificacionAdmin(admin.ModelAdmin):

    list_display = (
        "producto",
        "categoria",
        "frecuencia",
        "probabilidad",
        "parametro",
    )

    list_filter = (
        "categoria",
    )

    search_fields = (
        "producto__codigo",
        "producto__nombre",
    )