from django.urls import path

from . import views


app_name = "vehiculos"


urlpatterns = [
    path(
        "",
        views.listar_vehiculos,
        name="listar_vehiculos",
    ),

    path(
        "compatibilidades/",
        views.listar_compatibilidades,
        name="listar_compatibilidades",
    ),

    path(
        "compatibilidades/registrar/",
        views.registrar_compatibilidad,
        name="registrar_compatibilidad",
    ),

    path(
        "compatibilidades/modificar/<int:compatibilidad_id>/",
        views.modificar_compatibilidad,
        name="modificar_compatibilidad",
    ),

    path(
        "compatibilidades/eliminar/<int:compatibilidad_id>/",
        views.eliminar_compatibilidad,
        name="eliminar_compatibilidad",
    ),

    path(
        "registrar/",
        views.registrar_vehiculo,
        name="registrar_vehiculo",
    ),

    path(
        "modificar/<int:vehiculo_id>/",
        views.modificar_vehiculo,
        name="modificar_vehiculo",
    ),
    path(
    "cambiar-estado/<int:vehiculo_id>/",
    views.cambiar_estado_vehiculo,
    name="cambiar_estado_vehiculo",
),
]