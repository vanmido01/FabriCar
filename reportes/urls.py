from django.urls import path

from . import views


app_name = "reportes"


urlpatterns = [
    path(
        "",
        views.panel_reportes,
        name="panel_reportes",
    ),

    path(
        "ventas/",
        views.reporte_ventas,
        name="reporte_ventas",
    ),
    path(
        "ventas/pdf/",
        views.reporte_ventas_pdf,
        name="reporte_ventas_pdf",
    ),

    path(
        "compras/",
        views.reporte_compras,
        name="reporte_compras",
    ),
    path(
        "compras/pdf/",
        views.reporte_compras_pdf,
        name="reporte_compras_pdf",
    ),

    path(
        "creditos/",
        views.reporte_creditos,
        name="reporte_creditos",
    ),
    path(
        "creditos/pdf/",
        views.reporte_creditos_pdf,
        name="reporte_creditos_pdf",
    ),

    path(
        "bajo-stock/",
        views.reporte_bajo_stock,
        name="reporte_bajo_stock",
    ),
    path(
        "bajo-stock/pdf/",
        views.reporte_bajo_stock_pdf,
        name="reporte_bajo_stock_pdf",
    ),
]