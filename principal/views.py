from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .decorators import rol_requerido


@login_required
def inicio(request):
    """Muestra la página principal según el rol del usuario."""

    if request.user.is_superuser:
        rol_usuario = "Administrador"
    elif request.user.groups.filter(name="Administrador").exists():
        rol_usuario = "Administrador"
    elif request.user.groups.filter(name="Empleado").exists():
        rol_usuario = "Empleado"
    elif request.user.groups.filter(name="Cliente").exists():
        rol_usuario = "Cliente"
    else:
        rol_usuario = "Sin rol asignado"

    contexto = {
        "rol_usuario": rol_usuario,
    }

    return render(
        request,
        "principal/inicio.html",
        contexto,
    )

@login_required
def redirigir_por_rol(request):
    """Dirige al usuario hacia el panel correspondiente a su rol."""

    usuario = request.user

    if usuario.is_superuser:
        return redirect("panel_administrador")

    if usuario.groups.filter(name="Administrador").exists():
        return redirect("panel_administrador")

    if usuario.groups.filter(name="Empleado").exists():
        return redirect("panel_empleado")

    if usuario.groups.filter(name="Cliente").exists():
        return redirect("panel_cliente")

    return redirect("inicio")

@login_required
@rol_requerido("Administrador")
def panel_administrador(request):
    """Muestra una página exclusiva para administradores."""

    contexto = {
        "rol_usuario": "Administrador",
    }

    return render(
        request,
        "principal/panel_administrador.html",
        contexto,
    )
@login_required
@rol_requerido("Empleado")
def panel_empleado(request):
    """Muestra el panel operativo de los empleados."""

    contexto = {
        "rol_usuario": "Empleado",
    }

    return render(
        request,
        "principal/panel_empleado.html",
        contexto,
    )


@login_required
@rol_requerido("Cliente")
def panel_cliente(request):
    """Muestra el panel limitado destinado a clientes."""

    contexto = {
        "rol_usuario": "Cliente",
    }

    return render(
        request,
        "principal/panel_cliente.html",
        contexto,
    )