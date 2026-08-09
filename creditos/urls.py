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
        "<int:credito_id>/estado-cuenta-pdf/",
        views.estado_cuenta_credito_pdf,
        name="estado_cuenta_credito_pdf",
    ),
    path(
        "<int:credito_id>/pago/registrar/",
        views.registrar_pago,
        name="registrar_pago",
    ),
    path(
        "pago/<int:pago_id>/comprobante-pdf/",
        views.comprobante_pago_pdf,
        name="comprobante_pago_pdf",
    ),
    path(
        "<int:credito_id>/",
        views.detalle_credito,
        name="detalle_credito",
    ),
]