from django.urls import path

from . import views


app_name = "proveedores"


urlpatterns = [
    path(
        "",
        views.listar_proveedores,
        name="listar_proveedores",
    ),

    path(
        "registrar/",
        views.registrar_proveedor,
        name="registrar_proveedor",
    ),

    path(
        "modificar/<int:proveedor_id>/",
        views.modificar_proveedor,
        name="modificar_proveedor",
    ),

    path(
        "cambiar-estado/<int:proveedor_id>/",
        views.cambiar_estado_proveedor,
        name="cambiar_estado_proveedor",
    ),
]