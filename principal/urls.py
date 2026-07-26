from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path(
        "",
        views.inicio,
        name="inicio",
    ),
    path(
        "redirigir/",
        views.redirigir_por_rol,
        name="redirigir_por_rol",
    ),

    path(
        "panel-administrador/",
        views.panel_administrador,
        name="panel_administrador",
    ),

    path(
        "panel-empleado/",
        views.panel_empleado,
        name="panel_empleado",
    ),

    path(
        "panel-cliente/",
        views.panel_cliente,
        name="panel_cliente",
    ),

    path(
        "iniciar-sesion/",
        auth_views.LoginView.as_view(
            template_name="principal/iniciar_sesion.html",
            redirect_authenticated_user=True,
        ),
        name="iniciar_sesion",
    ),

    path(
        "cerrar-sesion/",
        auth_views.LogoutView.as_view(),
        name="cerrar_sesion",
    ),
]