from django.urls import path

from . import views


app_name = "inventario"


urlpatterns = [
    path(
        "",
        views.listar_movimientos,
        name="listar_movimientos",
    ),

    path(
        "ajuste/registrar/",
        views.registrar_ajuste,
        name="registrar_ajuste",
    ),
]