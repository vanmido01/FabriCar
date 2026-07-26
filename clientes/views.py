from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido

from .forms import ClienteForm
from .models import Cliente


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_clientes(request):
    """Muestra, busca, filtra y pagina los clientes registrados."""

    busqueda = request.GET.get("q", "").strip()
    filtro_tipo = request.GET.get("tipo", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    clientes = Cliente.objects.all()

    if busqueda:
        clientes = clientes.filter(
            Q(nombre__icontains=busqueda)
            | Q(documento__icontains=busqueda)
            | Q(telefono__icontains=busqueda)
            | Q(correo__icontains=busqueda)
        )

    tipos_validos = {
        Cliente.TipoCliente.PARTICULAR,
        Cliente.TipoCliente.TALLER,
        Cliente.TipoCliente.INSTITUCION,
    }

    if filtro_tipo in tipos_validos:
        clientes = clientes.filter(
            tipo_cliente=filtro_tipo
        )

    if filtro_estado == "activo":
        clientes = clientes.filter(estado=True)

    elif filtro_estado == "inactivo":
        clientes = clientes.filter(estado=False)

    clientes = clientes.order_by("nombre")

    paginador = Paginator(clientes, 10)
    numero_pagina = request.GET.get("page")
    pagina_clientes = paginador.get_page(numero_pagina)

    puede_gestionar_clientes = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "clientes": pagina_clientes,
        "pagina_clientes": pagina_clientes,
        "busqueda": busqueda,
        "filtro_tipo": filtro_tipo,
        "filtro_estado": filtro_estado,
        "puede_gestionar_clientes": puede_gestionar_clientes,
    }

    return render(
        request,
        "clientes/listar_clientes.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador")
def registrar_cliente(request):
    """Registra un nuevo cliente en el sistema."""

    if request.method == "POST":
        formulario = ClienteForm(request.POST)

        if formulario.is_valid():
            cliente = formulario.save()

            messages.success(
                request,
                (
                    f'El cliente "{cliente.nombre}" '
                    "fue registrado correctamente."
                ),
            )

            return redirect("clientes:listar_clientes")

    else:
        formulario = ClienteForm()

    contexto = {
        "formulario": formulario,
        "modo_edicion": False,
    }

    return render(
        request,
        "clientes/registrar_cliente.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def modificar_cliente(request, cliente_id):
    """Modifica la información de un cliente registrado."""

    cliente = get_object_or_404(
        Cliente,
        id=cliente_id,
    )

    if request.method == "POST":
        formulario = ClienteForm(
            request.POST,
            instance=cliente,
        )

        if formulario.is_valid():
            cliente = formulario.save()

            messages.success(
                request,
                (
                    f'El cliente "{cliente.nombre}" '
                    "fue modificado correctamente."
                ),
            )

            return redirect("clientes:listar_clientes")

    else:
        formulario = ClienteForm(
            instance=cliente,
        )

    contexto = {
        "formulario": formulario,
        "cliente": cliente,
        "modo_edicion": True,
    }

    return render(
        request,
        "clientes/registrar_cliente.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def cambiar_estado_cliente(request, cliente_id):
    """Activa o desactiva un cliente registrado."""

    cliente = get_object_or_404(
        Cliente,
        id=cliente_id,
    )

    if request.method == "POST":
        cliente.estado = not cliente.estado

        cliente.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        if cliente.estado:
            messages.success(
                request,
                (
                    f'El cliente "{cliente.nombre}" '
                    "fue activado correctamente."
                ),
            )
        else:
            messages.success(
                request,
                (
                    f'El cliente "{cliente.nombre}" '
                    "fue desactivado correctamente."
                ),
            )

    return redirect("clientes:listar_clientes")