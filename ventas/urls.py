from django.urls import path

from . import views


app_name = "ventas"


urlpatterns = [
    path(
        "",
        views.listar_ventas,
        name="listar_ventas",
    ),
    path(
        "registrar/",
        views.registrar_venta,
        name="registrar_venta",
    ),
    path(
        "<int:venta_id>/editar/",
        views.editar_venta,
        name="editar_venta",
    ),
    path(
        "<int:venta_id>/confirmar/",
        views.confirmar_venta,
        name="confirmar_venta",
    ),
    path(
        "<int:venta_id>/anular/",
        views.anular_venta,
        name="anular_venta",
    ),
    path(
        "<int:venta_id>/",
        views.detalle_venta,
        name="detalle_venta",
    ),
]