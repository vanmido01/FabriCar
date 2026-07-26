from django.urls import path

from . import views


app_name = "creditos"


urlpatterns = [
    path(
        "",
        views.listar_creditos,
        name="listar_creditos",
    ),
    path(
        "<int:credito_id>/editar/",
        views.editar_credito,
        name="editar_credito",
    ),
    path(
        "<int:credito_id>/pago/registrar/",
        views.registrar_pago,
        name="registrar_pago",
    ),
    path(
        "<int:credito_id>/",
        views.detalle_credito,
        name="detalle_credito",
    ),
]