from django.urls import path

from . import views

app_name = "clasificacion"

urlpatterns = [

    path(
        "",
        views.clasificacion_automatica,
        name="clasificacion_automatica",
    ),

    path(
        "pdf/<int:parametro_id>/",
        views.clasificacion_pdf,
        name="clasificacion_pdf",
    ),
]