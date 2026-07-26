from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido

from .forms import ProductoForm
from .models import Producto
from django.db.models import Q
from django.core.paginator import Paginator


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_productos(request):
    """Muestra, busca, filtra y pagina los productos registrados."""

    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    productos = Producto.objects.all()

    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(marca__icontains=busqueda)
        )

    if filtro_estado == "activo":
        productos = productos.filter(estado=True)

    elif filtro_estado == "inactivo":
        productos = productos.filter(estado=False)

    productos = productos.order_by("nombre")

    paginador = Paginator(productos, 10)

    numero_pagina = request.GET.get("page")

    pagina_productos = paginador.get_page(numero_pagina)

    puede_gestionar_productos = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "productos": pagina_productos,
        "pagina_productos": pagina_productos,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "puede_gestionar_productos": puede_gestionar_productos,
    }

    return render(
        request,
        "productos/listar_productos.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def detalle_producto(request, producto_id):
    """Muestra la información completa y compatibilidades del producto."""

    producto = get_object_or_404(
        Producto,
        id=producto_id,
    )

    compatibilidades = (
        producto.compatibilidades
        .select_related("vehiculo")
        .order_by(
            "vehiculo__marca",
            "vehiculo__modelo",
            "vehiculo__anio_desde",
        )
    )

    puede_gestionar_productos = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "producto": producto,
        "compatibilidades": compatibilidades,
        "puede_gestionar_productos": puede_gestionar_productos,
    }

    return render(
        request,
        "productos/detalle_producto.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def registrar_producto(request):
    """Registra un nuevo producto en el sistema."""

    if request.method == "POST":
        formulario = ProductoForm(
            request.POST,
            request.FILES,
        )

        if formulario.is_valid():
            producto = formulario.save()

            messages.success(
                request,
                f'El producto "{producto.nombre}" '
                "fue registrado correctamente.",
            )

            return redirect("productos:listar_productos")

    else:
        formulario = ProductoForm()

    contexto = {
        "formulario": formulario,
        "modo_edicion": False,
    }

    return render(
        request,
        "productos/registrar_producto.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador")
def modificar_producto(request, producto_id):
    """Modifica la información de un producto registrado."""

    producto = get_object_or_404(
        Producto,
        id=producto_id,
    )

    if request.method == "POST":
        formulario = ProductoForm(
            request.POST,
            request.FILES,
            instance=producto,
        )

        if formulario.is_valid():
            producto = formulario.save()

            messages.success(
                request,
                f'El producto "{producto.nombre}" '
                "fue modificado correctamente.",
            )

            return redirect("productos:listar_productos")

    else:
        formulario = ProductoForm(
            instance=producto,
        )

    contexto = {
        "formulario": formulario,
        "producto": producto,
        "modo_edicion": True,
    }

    return render(
        request,
        "productos/registrar_producto.html",
        contexto,
    )
@login_required
@rol_requerido("Administrador")
def cambiar_estado_producto(request, producto_id):
    """Activa o desactiva un producto registrado."""

    producto = get_object_or_404(
        Producto,
        id=producto_id,
    )

    if request.method == "POST":
        producto.estado = not producto.estado
        producto.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        if producto.estado:
            messages.success(
                request,
                f'El producto "{producto.nombre}" fue activado correctamente.',
            )
        else:
            messages.success(
                request,
                f'El producto "{producto.nombre}" fue desactivado correctamente.',
            )

    return redirect("productos:listar_productos")