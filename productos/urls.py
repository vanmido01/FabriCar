from django.urls import path

from . import views


app_name = "productos"


urlpatterns = [
    path(
        "",
        views.listar_productos,
        name="listar_productos",
    ),
    path(
        "detalle/<int:producto_id>/",
        views.detalle_producto,
        name="detalle_producto",
    ),
    path(
        "registrar/",
        views.registrar_producto,
        name="registrar_producto",
    ),

    path(
        "modificar/<int:producto_id>/",
        views.modificar_producto,
        name="modificar_producto",
    ),
    path(
        "cambiar-estado/<int:producto_id>/",
        views.cambiar_estado_producto,
        name="cambiar_estado_producto",
    ),
]