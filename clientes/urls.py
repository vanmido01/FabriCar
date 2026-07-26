from django.urls import path

from . import views


app_name = "clientes"


urlpatterns = [
    path(
        "",
        views.listar_clientes,
        name="listar_clientes",
    ),

    path(
        "registrar/",
        views.registrar_cliente,
        name="registrar_cliente",
    ),

    path(
        "modificar/<int:cliente_id>/",
        views.modificar_cliente,
        name="modificar_cliente",
    ),

    path(
        "cambiar-estado/<int:cliente_id>/",
        views.cambiar_estado_cliente,
        name="cambiar_estado_cliente",
    ),
]