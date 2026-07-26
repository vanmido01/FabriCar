from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render

from principal.decorators import rol_requerido
from productos.models import Producto

from .forms import AjusteInventarioForm
from .models import MovimientoInventario


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_movimientos(request):
    """Muestra, busca, filtra y pagina los movimientos del inventario."""

    busqueda = request.GET.get("q", "").strip()
    filtro_tipo = request.GET.get("tipo", "").strip()

    movimientos = (
        MovimientoInventario.objects.select_related(
            "producto",
            "compra",
            "venta",
            "usuario",
        )
        
    )
    

    if busqueda:
        movimientos = movimientos.filter(
            Q(producto__codigo__icontains=busqueda)
            | Q(producto__nombre__icontains=busqueda)
            | Q(motivo__icontains=busqueda)
            | Q(observaciones__icontains=busqueda)
            | Q(compra__numero_comprobante__icontains=busqueda)
            | Q(venta__numero_comprobante__icontains=busqueda)
            | Q(usuario__username__icontains=busqueda)
        )

    tipos_validos = {
        MovimientoInventario.TipoMovimiento.ENTRADA_COMPRA,
        MovimientoInventario.TipoMovimiento.SALIDA_VENTA,
        MovimientoInventario.TipoMovimiento.AJUSTE_ENTRADA,
        MovimientoInventario.TipoMovimiento.AJUSTE_SALIDA,
    }

    if filtro_tipo in tipos_validos:
        movimientos = movimientos.filter(
            tipo_movimiento=filtro_tipo,
        )

    movimientos = movimientos.order_by(
        "-fecha_movimiento",
        "-id",
    )

    paginador = Paginator(movimientos, 10)
    numero_pagina = request.GET.get("page")
    pagina_movimientos = paginador.get_page(numero_pagina)

    puede_registrar_ajuste = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "movimientos": pagina_movimientos,
        "pagina_movimientos": pagina_movimientos,
        "busqueda": busqueda,
        "filtro_tipo": filtro_tipo,
        "puede_registrar_ajuste": puede_registrar_ajuste,
    }

    return render(
        request,
        "inventario/listar_movimientos.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador")
def registrar_ajuste(request):
    """Registra un ajuste manual y actualiza el stock del producto."""

    if request.method == "POST":
        formulario = AjusteInventarioForm(request.POST)

        if formulario.is_valid():
            producto_seleccionado = formulario.cleaned_data[
                "producto"
            ]
            tipo_ajuste = formulario.cleaned_data[
                "tipo_ajuste"
            ]
            cantidad = formulario.cleaned_data[
                "cantidad"
            ]
            motivo = formulario.cleaned_data[
                "motivo"
            ]
            observaciones = formulario.cleaned_data[
                "observaciones"
            ]

            ajuste_registrado = False

            with transaction.atomic():
                producto = (
                    Producto.objects
                    .select_for_update()
                    .filter(
                        id=producto_seleccionado.id,
                        estado=True,
                    )
                    .first()
                )

                if producto is None:
                    formulario.add_error(
                        "producto",
                        (
                            "El producto seleccionado no existe "
                            "o se encuentra inactivo."
                        ),
                    )

                else:
                    stock_anterior = producto.stock_actual

                    if (
                        tipo_ajuste
                        == MovimientoInventario
                        .TipoMovimiento
                        .AJUSTE_SALIDA
                    ):
                        if cantidad > stock_anterior:
                            formulario.add_error(
                                "cantidad",
                                (
                                    "La cantidad de salida no puede "
                                    "ser mayor al stock disponible de "
                                    f"{stock_anterior}."
                                ),
                            )

                        else:
                            stock_posterior = (
                                stock_anterior - cantidad
                            )

                    else:
                        stock_posterior = (
                            stock_anterior + cantidad
                        )

                    if not formulario.errors:
                        producto.stock_actual = stock_posterior

                        producto.save(
                            update_fields=[
                                "stock_actual",
                                "fecha_modificacion",
                            ]
                        )

                        MovimientoInventario.objects.create(
                            producto=producto,
                            tipo_movimiento=tipo_ajuste,
                            cantidad=cantidad,
                            stock_anterior=stock_anterior,
                            stock_posterior=stock_posterior,
                            motivo=motivo,
                            observaciones=observaciones,
                            usuario=request.user,
                        )

                        ajuste_registrado = True

            if ajuste_registrado:
                messages.success(
                    request,
                    (
                        f'El ajuste del producto '
                        f'"{producto.nombre}" fue registrado '
                        "correctamente."
                    ),
                )

                return redirect(
                    "inventario:listar_movimientos"
                )

    else:
        formulario = AjusteInventarioForm()

    contexto = {
        "formulario": formulario,
    }

    return render(
        request,
        "inventario/registrar_ajuste.html",
        contexto,
    )