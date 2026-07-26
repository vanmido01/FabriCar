from django.urls import path

from . import views


app_name = "compras"


urlpatterns = [
    path(
        "",
        views.listar_compras,
        name="listar_compras",
    ),

    path(
        "detalle/<int:compra_id>/",
        views.detalle_compra,
        name="detalle_compra",
    ),

    path(
        "registrar/",
        views.registrar_compra,
        name="registrar_compra",
    ),

    path(
        "modificar/<int:compra_id>/",
        views.modificar_compra,
        name="modificar_compra",
    ),

    path(
        "confirmar/<int:compra_id>/",
        views.confirmar_compra,
        name="confirmar_compra",
    ),

    path(
        "anular/<int:compra_id>/",
        views.anular_compra,
        name="anular_compra",
    ),
]