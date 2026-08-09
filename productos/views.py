from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido
from vehiculos.models import CompatibilidadProducto

from .forms import ProductoForm
from .models import Producto


def sincronizar_compatibilidades(producto, vehiculos):
    """
    Mantiene sincronizados los vehículos compatibles del producto.

    Conserva las relaciones seleccionadas, crea las nuevas
    y elimina únicamente las que el usuario desmarcó.
    """

    vehiculos_ids = list(
        vehiculos.values_list(
            "id",
            flat=True,
        )
    )

    if vehiculos_ids:
        producto.compatibilidades.exclude(
            vehiculo_id__in=vehiculos_ids,
        ).delete()
    else:
        producto.compatibilidades.all().delete()

    for vehiculo_id in vehiculos_ids:
        CompatibilidadProducto.objects.get_or_create(
            producto=producto,
            vehiculo_id=vehiculo_id,
        )


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_productos(request):
    """Muestra, busca, filtra y pagina los productos registrados."""

    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    productos = Producto.objects.annotate(
        cantidad_proveedores=Count(
            "proveedores_habituales",
            distinct=True,
        ),
        cantidad_vehiculos=Count(
            "compatibilidades",
            distinct=True,
        ),
    )

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
    """Registra una nueva ficha de producto."""

    if request.method == "POST":
        formulario = ProductoForm(
            request.POST,
            request.FILES,
        )

        if formulario.is_valid():

            with transaction.atomic():
                producto = formulario.save(
                    commit=False,
                )

                producto.precio_compra = Decimal("0.00")
                producto.precio_venta = Decimal("0.00")
                producto.stock_actual = 0
                producto.stock_minimo = 0

                producto.save()

                # Guarda los proveedores habituales.
                formulario.save_m2m()

                # Guarda todos los vehículos seleccionados.
                sincronizar_compatibilidades(
                    producto,
                    formulario.cleaned_data[
                        "vehiculos_compatibles"
                    ],
                )

            messages.success(
                request,
                (
                    f'El producto "{producto.nombre}" '
                    "fue registrado correctamente."
                ),
            )

            return redirect(
                "productos:detalle_producto",
                producto_id=producto.id,
            )

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
    """Modifica la ficha y sus relaciones asociadas."""

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

            with transaction.atomic():
                producto = formulario.save(
                    commit=False,
                )

                producto.save()

                # Actualiza los proveedores seleccionados.
                formulario.save_m2m()

                # Actualiza los vehículos compatibles.
                sincronizar_compatibilidades(
                    producto,
                    formulario.cleaned_data[
                        "vehiculos_compatibles"
                    ],
                )

            messages.success(
                request,
                (
                    f'El producto "{producto.nombre}" '
                    "fue modificado correctamente."
                ),
            )

            return redirect(
                "productos:detalle_producto",
                producto_id=producto.id,
            )

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
        Producto.objects.prefetch_related(
            "proveedores_habituales",
        ),
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