from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido

from .forms import ProveedorForm
from .models import Proveedor


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_proveedores(request):
    """Muestra, busca, filtra y pagina los proveedores registrados."""

    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    proveedores = Proveedor.objects.all()

    if busqueda:
        proveedores = proveedores.filter(
            Q(razon_social__icontains=busqueda)
            | Q(nit__icontains=busqueda)
            | Q(persona_contacto__icontains=busqueda)
            | Q(telefono__icontains=busqueda)
            | Q(correo__icontains=busqueda)
        )

    if filtro_estado == "activo":
        proveedores = proveedores.filter(estado=True)

    elif filtro_estado == "inactivo":
        proveedores = proveedores.filter(estado=False)

    proveedores = proveedores.order_by("razon_social")

    paginador = Paginator(proveedores, 10)
    numero_pagina = request.GET.get("page")
    pagina_proveedores = paginador.get_page(numero_pagina)

    puede_gestionar_proveedores = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "proveedores": pagina_proveedores,
        "pagina_proveedores": pagina_proveedores,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "puede_gestionar_proveedores": (
            puede_gestionar_proveedores
        ),
    }

    return render(
        request,
        "proveedores/listar_proveedores.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador")
def registrar_proveedor(request):
    """Registra un nuevo proveedor en el sistema."""

    if request.method == "POST":
        formulario = ProveedorForm(request.POST)

        if formulario.is_valid():
            proveedor = formulario.save()

            messages.success(
                request,
                (
                    f'El proveedor "{proveedor.razon_social}" '
                    "fue registrado correctamente."
                ),
            )

            return redirect(
                "proveedores:listar_proveedores"
            )

    else:
        formulario = ProveedorForm()

    contexto = {
        "formulario": formulario,
        "modo_edicion": False,
    }

    return render(
        request,
        "proveedores/registrar_proveedor.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def modificar_proveedor(request, proveedor_id):
    """Modifica la información de un proveedor registrado."""

    proveedor = get_object_or_404(
        Proveedor,
        id=proveedor_id,
    )

    if request.method == "POST":
        formulario = ProveedorForm(
            request.POST,
            instance=proveedor,
        )

        if formulario.is_valid():
            proveedor = formulario.save()

            messages.success(
                request,
                (
                    f'El proveedor "{proveedor.razon_social}" '
                    "fue modificado correctamente."
                ),
            )

            return redirect(
                "proveedores:listar_proveedores"
            )

    else:
        formulario = ProveedorForm(
            instance=proveedor,
        )

    contexto = {
        "formulario": formulario,
        "proveedor": proveedor,
        "modo_edicion": True,
    }

    return render(
        request,
        "proveedores/registrar_proveedor.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def cambiar_estado_proveedor(request, proveedor_id):
    """Activa o desactiva un proveedor registrado."""

    proveedor = get_object_or_404(
        Proveedor,
        id=proveedor_id,
    )

    if request.method == "POST":
        proveedor.estado = not proveedor.estado

        proveedor.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        if proveedor.estado:
            messages.success(
                request,
                (
                    f'El proveedor "{proveedor.razon_social}" '
                    "fue activado correctamente."
                ),
            )
        else:
            messages.success(
                request,
                (
                    f'El proveedor "{proveedor.razon_social}" '
                    "fue desactivado correctamente."
                ),
            )

    return redirect(
        "proveedores:listar_proveedores"
    )