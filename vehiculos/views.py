from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido

from .forms import CompatibilidadProductoForm, VehiculoForm
from .models import CompatibilidadProducto, Vehiculo


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_vehiculos(request):
    """Muestra, busca, filtra y pagina los vehículos registrados."""

    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    vehiculos = Vehiculo.objects.all()

    if busqueda:
        vehiculos = vehiculos.filter(
            Q(marca__icontains=busqueda)
            | Q(modelo__icontains=busqueda)
            | Q(motor__icontains=busqueda)
        )

    if filtro_estado == "activo":
        vehiculos = vehiculos.filter(estado=True)

    elif filtro_estado == "inactivo":
        vehiculos = vehiculos.filter(estado=False)

    vehiculos = vehiculos.order_by(
        "marca",
        "modelo",
        "anio_desde",
    )

    paginador = Paginator(vehiculos, 10)

    numero_pagina = request.GET.get("page")

    pagina_vehiculos = paginador.get_page(numero_pagina)

    puede_gestionar_vehiculos = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "vehiculos": pagina_vehiculos,
        "pagina_vehiculos": pagina_vehiculos,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "puede_gestionar_vehiculos": puede_gestionar_vehiculos,
    }

    return render(
        request,
        "vehiculos/listar_vehiculos.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def listar_compatibilidades(request):
    """Muestra, busca y pagina las compatibilidades registradas."""

    busqueda = request.GET.get("q", "").strip()

    compatibilidades = (
        CompatibilidadProducto.objects
        .select_related(
            "producto",
            "vehiculo",
        )
    )

    if busqueda:
        compatibilidades = compatibilidades.filter(
            Q(producto__codigo__icontains=busqueda)
            | Q(producto__nombre__icontains=busqueda)
            | Q(vehiculo__marca__icontains=busqueda)
            | Q(vehiculo__modelo__icontains=busqueda)
            | Q(vehiculo__motor__icontains=busqueda)
        )

    compatibilidades = compatibilidades.order_by(
        "producto__nombre",
        "vehiculo__marca",
        "vehiculo__modelo",
    )

    paginador = Paginator(compatibilidades,10,)

    numero_pagina = request.GET.get("page")

    pagina_compatibilidades = paginador.get_page(
        numero_pagina
    )

    puede_gestionar_compatibilidades = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "compatibilidades": pagina_compatibilidades,
        "pagina_compatibilidades": pagina_compatibilidades,
        "busqueda": busqueda,
        "puede_gestionar_compatibilidades": (
            puede_gestionar_compatibilidades
        ),
    }

    return render(
        request,
        "vehiculos/listar_compatibilidades.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def registrar_compatibilidad(request):
    """Registra una compatibilidad entre un producto y un vehículo."""

    if request.method == "POST":
        formulario = CompatibilidadProductoForm(request.POST)

        if formulario.is_valid():
            compatibilidad = formulario.save()

            messages.success(
                request,
                (
                    f'La compatibilidad entre el producto '
                    f'"{compatibilidad.producto.nombre}" y el vehículo '
                    f'"{compatibilidad.vehiculo}" fue registrada correctamente.'
                ),
            )

            return redirect(
                "vehiculos:listar_compatibilidades"
            )

    else:
        formulario = CompatibilidadProductoForm()

    contexto = {
        "formulario": formulario,
        "modo_edicion": False,
    }

    return render(
        request,
        "vehiculos/registrar_compatibilidad.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def modificar_compatibilidad(request, compatibilidad_id):
    """Modifica una compatibilidad registrada."""

    compatibilidad = get_object_or_404(
        CompatibilidadProducto,
        id=compatibilidad_id,
    )

    if request.method == "POST":
        formulario = CompatibilidadProductoForm(
            request.POST,
            instance=compatibilidad,
        )

        if formulario.is_valid():
            compatibilidad = formulario.save()

            messages.success(
                request,
                (
                    f'La compatibilidad entre el producto '
                    f'"{compatibilidad.producto.nombre}" y el vehículo '
                    f'"{compatibilidad.vehiculo}" fue modificada '
                    f"correctamente."
                ),
            )

            return redirect(
                "vehiculos:listar_compatibilidades"
            )

    else:
        formulario = CompatibilidadProductoForm(
            instance=compatibilidad,
        )

    contexto = {
        "formulario": formulario,
        "compatibilidad": compatibilidad,
        "modo_edicion": True,
    }

    return render(
        request,
        "vehiculos/registrar_compatibilidad.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def eliminar_compatibilidad(request, compatibilidad_id):
    """Elimina una compatibilidad registrada."""

    compatibilidad = get_object_or_404(
        CompatibilidadProducto,
        id=compatibilidad_id,
    )

    if request.method == "POST":
        nombre_producto = compatibilidad.producto.nombre
        nombre_vehiculo = str(compatibilidad.vehiculo)

        compatibilidad.delete()

        messages.success(
            request,
            (
                f'La compatibilidad entre el producto '
                f'"{nombre_producto}" y el vehículo '
                f'"{nombre_vehiculo}" fue eliminada correctamente.'
            ),
        )

    return redirect(
        "vehiculos:listar_compatibilidades"
    )

@login_required
@rol_requerido("Administrador")
def registrar_vehiculo(request):
    """Registra un nuevo vehículo en el sistema."""

    if request.method == "POST":
        formulario = VehiculoForm(request.POST)

        if formulario.is_valid():
            vehiculo = formulario.save()

            messages.success(
                request,
                (
                    f'El vehículo "{vehiculo.marca} '
                    f'{vehiculo.modelo}" fue registrado correctamente.'
                ),
            )

            return redirect("vehiculos:listar_vehiculos")

    else:
        formulario = VehiculoForm()

    contexto = {
        "formulario": formulario,
        "modo_edicion": False,
    }

    return render(
        request,
        "vehiculos/registrar_vehiculo.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def modificar_vehiculo(request, vehiculo_id):
    """Modifica la información de un vehículo registrado."""

    vehiculo = get_object_or_404(
        Vehiculo,
        id=vehiculo_id,
    )

    if request.method == "POST":
        formulario = VehiculoForm(
            request.POST,
            instance=vehiculo,
        )

        if formulario.is_valid():
            vehiculo = formulario.save()

            messages.success(
                request,
                (
                    f'El vehículo "{vehiculo.marca} '
                    f'{vehiculo.modelo}" fue modificado correctamente.'
                ),
            )

            return redirect("vehiculos:listar_vehiculos")

    else:
        formulario = VehiculoForm(
            instance=vehiculo,
        )

    contexto = {
        "formulario": formulario,
        "vehiculo": vehiculo,
        "modo_edicion": True,
    }

    return render(
        request,
        "vehiculos/registrar_vehiculo.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def cambiar_estado_vehiculo(request, vehiculo_id):
    """Activa o desactiva un vehículo registrado."""

    vehiculo = get_object_or_404(
        Vehiculo,
        id=vehiculo_id,
    )

    if request.method == "POST":
        vehiculo.estado = not vehiculo.estado

        vehiculo.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        if vehiculo.estado:
            messages.success(
                request,
                (
                    f'El vehículo "{vehiculo.marca} '
                    f'{vehiculo.modelo}" fue activado correctamente.'
                ),
            )
        else:
            messages.success(
                request,
                (
                    f'El vehículo "{vehiculo.marca} '
                    f'{vehiculo.modelo}" fue desactivado correctamente.'
                ),
            )

    return redirect("vehiculos:listar_vehiculos")