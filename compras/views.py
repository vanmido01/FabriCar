from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from decimal import Decimal

from principal.decorators import rol_requerido
from .forms import CompraForm, DetalleCompraFormSet
from .models import Compra

from django.views.decorators.http import require_POST
from inventario.models import MovimientoInventario
from productos.models import Producto


def obtener_precios_vigentes_productos():
    """
    Devuelve los precios actuales de los productos activos.

    Los valores se convierten a texto para poder utilizarlos
    de forma segura dentro del código JavaScript de la plantilla.
    """

    productos = (
        Producto.objects
        .filter(estado=True)
        .values(
            "id",
            "precio_compra",
            "precio_venta",
        )
    )

    return {
        str(producto["id"]): {
            "costo_compra": str(producto["precio_compra"]),
            "precio_venta": str(producto["precio_venta"]),
        }
        for producto in productos
    }

def confirmar_compra_en_transaccion(compra, usuario):
    """
    Confirma una compra dentro de una transacción abierta.

    Actualiza existencias, precios y movimientos de inventario.
    Devuelve un mensaje de error o None cuando termina correctamente.
    """

    if compra.estado != Compra.EstadoCompra.BORRADOR:
        return (
            "La compra no puede confirmarse porque "
            "ya fue confirmada o anulada."
        )

    detalles = list(
        compra.detalles.select_related(
            "producto",
        )
    )

    if not detalles:
        return "La compra no tiene productos registrados."

    for detalle in detalles:
        producto = Producto.objects.select_for_update().get(
            id=detalle.producto_id,
        )

        stock_anterior = producto.stock_actual
        stock_posterior = (
            stock_anterior + detalle.cantidad
        )

        producto.stock_actual = stock_posterior
        producto.precio_compra = detalle.costo_unitario
        producto.precio_venta = detalle.precio_venta

        producto.save(
            update_fields=[
                "stock_actual",
                "precio_compra",
                "precio_venta",
                "fecha_modificacion",
            ]
        )

        MovimientoInventario.objects.create(
            producto=producto,
            tipo_movimiento=(
                MovimientoInventario
                .TipoMovimiento
                .ENTRADA_COMPRA
            ),
            cantidad=detalle.cantidad,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior,
            compra=compra,
            motivo=(
                f"Confirmación de la compra "
                f"N.º {compra.id}"
            ),
            observaciones=compra.observaciones,
            usuario=usuario,
        )

    # Debe quedar fuera del ciclo for.
    compra.estado = Compra.EstadoCompra.CONFIRMADA
    compra.usuario_confirmacion = usuario
    compra.fecha_confirmacion = timezone.now()

    compra.save(
        update_fields=[
            "estado",
            "usuario_confirmacion",
            "fecha_confirmacion",
            "fecha_modificacion",
        ]
    )

    return None


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_compras(request):
    """Muestra, busca, filtra y pagina las compras registradas."""

    busqueda = request.GET.get("q", "").strip()
    filtro_estado = request.GET.get("estado", "").strip()

    compras = (
        Compra.objects
        .select_related(
            "proveedor",
            "usuario_registro",
            "usuario_confirmacion",
            "usuario_anulacion",
        )
        .annotate(
            cantidad_productos=Count(
                "detalles",
                distinct=True,
            )
        )
    )

    if busqueda:
        compras = compras.filter(
            Q(proveedor__razon_social__icontains=busqueda)
            | Q(proveedor__nit__icontains=busqueda)
            | Q(numero_comprobante__icontains=busqueda)
        )

    estados_validos = {
        Compra.EstadoCompra.BORRADOR,
        Compra.EstadoCompra.CONFIRMADA,
        Compra.EstadoCompra.ANULADA,
    }

    if filtro_estado in estados_validos:
        compras = compras.filter(
            estado=filtro_estado,
        )

    compras = compras.order_by(
        "-fecha_compra",
        "-id",
    )

    paginador = Paginator(compras, 10)
    numero_pagina = request.GET.get("page")
    pagina_compras = paginador.get_page(numero_pagina)

    puede_gestionar_compras = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "compras": pagina_compras,
        "pagina_compras": pagina_compras,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "puede_gestionar_compras": puede_gestionar_compras,
    }

    return render(
        request,
        "compras/listar_compras.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def detalle_compra(request, compra_id):
    """Muestra la información completa de una compra."""

    compra = get_object_or_404(
        Compra.objects.select_related(
            "proveedor",
            "usuario_registro",
            "usuario_confirmacion",
            "usuario_anulacion",
        ).prefetch_related(
            "detalles__producto",
        ),
        id=compra_id,
    )

    puede_gestionar_compras = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="Administrador"
        ).exists()
    )

    contexto = {
        "compra": compra,
        "detalles": compra.detalles.all(),
        "puede_gestionar_compras": puede_gestionar_compras,
    }

    return render(
        request,
        "compras/detalle_compra.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador")
def registrar_compra(request):
    """Registra una compra y sus productos en estado borrador."""

    compra = Compra(
        usuario_registro=request.user,
        estado=Compra.EstadoCompra.BORRADOR,
    )

    if request.method == "POST":
        accion = request.POST.get(
            "accion",
            "borrador",
        )

        formulario = CompraForm(
            request.POST,
            instance=compra,
        )

        formulario_detalles = DetalleCompraFormSet(
            request.POST,
            instance=compra,
            prefix="detalles",
        )

        if formulario.is_valid() and formulario_detalles.is_valid():

            error_confirmacion = None

            with transaction.atomic():
                compra = formulario.save(commit=False)

                compra.usuario_registro = request.user
                compra.estado = Compra.EstadoCompra.BORRADOR
                compra.save()

                formulario_detalles.instance = compra
                formulario_detalles.save()

                compra.actualizar_total()

                if accion == "confirmar":
                    error_confirmacion = (
                        confirmar_compra_en_transaccion(
                            compra,
                            request.user,
                        )
                    )

            if error_confirmacion:
                messages.error(
                    request,
                    error_confirmacion,
                )

                return redirect(
                    "compras:detalle_compra",
                    compra_id=compra.id,
                )

            if accion == "confirmar":
                messages.success(
                    request,
                    (
                        f"La compra N.º {compra.id} fue registrada "
                        "y confirmada correctamente. "
                        "El inventario y los precios fueron actualizados."
                    ),
                )

                return redirect(
                    "compras:detalle_compra",
                    compra_id=compra.id,
                )

            messages.success(
                request,
                (
                    f"La compra N.º {compra.id} fue registrada "
                    "correctamente en estado borrador."
                ),
            )

            return redirect(
                "compras:detalle_compra",
                compra_id=compra.id,
            )

    else:
        formulario = CompraForm(
            instance=compra,
        )

        formulario_detalles = DetalleCompraFormSet(
            instance=compra,
            prefix="detalles",
        )

    contexto = {
        "formulario": formulario,
        "formulario_detalles": formulario_detalles,
         "modo_edicion": False,
         "precios_productos": obtener_precios_vigentes_productos(),
    }

    return render(
        request,
        "compras/registrar_compra.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
def modificar_compra(request, compra_id):
    """Modifica una compra que permanece en estado borrador."""

    compra = get_object_or_404(
        Compra,
        id=compra_id,
    )

    if compra.estado != Compra.EstadoCompra.BORRADOR:
        messages.error(
            request,
            (
                "La compra no puede modificarse porque "
                "ya fue confirmada o anulada."
            ),
        )

        return redirect(
            "compras:detalle_compra",
            compra_id=compra.id,
        )

    if request.method == "POST":
        formulario = CompraForm(
            request.POST,
            instance=compra,
        )

        formulario_detalles = DetalleCompraFormSet(
            request.POST,
            instance=compra,
            prefix="detalles",
        )

        if formulario.is_valid() and formulario_detalles.is_valid():

            with transaction.atomic():
                compra = formulario.save(commit=False)

                compra.estado = Compra.EstadoCompra.BORRADOR
                compra.save()

                formulario_detalles.instance = compra
                formulario_detalles.save()

                compra.actualizar_total()

            messages.success(
                request,
                (
                    f"La compra N.º {compra.id} "
                    "fue modificada correctamente."
                ),
            )

            return redirect(
                "compras:detalle_compra",
                compra_id=compra.id,
            )

    else:
        formulario = CompraForm(
            instance=compra,
        )

        formulario_detalles = DetalleCompraFormSet(
            instance=compra,
            prefix="detalles",
        )

    contexto = {
        "formulario": formulario,
        "formulario_detalles": formulario_detalles,
        "compra": compra,
        "modo_edicion": True,
        "precios_productos": obtener_precios_vigentes_productos(),
    }

    return render(
        request,
        "compras/registrar_compra.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador")
@require_POST
def confirmar_compra(request, compra_id):
    """Confirma una compra y actualiza el inventario."""

    with transaction.atomic():
        compra = get_object_or_404(
            Compra.objects.select_for_update(),
            id=compra_id,
        )

        error_confirmacion = (
            confirmar_compra_en_transaccion(
                compra,
                request.user,
            )
        )

    if error_confirmacion:
        messages.error(
            request,
            error_confirmacion,
        )
    else:
        messages.success(
            request,
            (
                f"La compra N.º {compra.id} fue confirmada. "
                "El inventario se actualizó correctamente."
            ),
        )

    return redirect(
        "compras:detalle_compra",
        compra_id=compra.id,
    )

@login_required
@rol_requerido("Administrador")
@require_POST
def anular_compra(request, compra_id):
    """Anula una compra y revierte el inventario si fue confirmada."""

    motivo_anulacion = request.POST.get(
        "motivo_anulacion",
        "",
    ).strip()

    if len(motivo_anulacion) < 5:
        messages.error(
            request,
            (
                "Debe escribir un motivo de anulación "
                "de al menos 5 caracteres."
            ),
        )

        return redirect(
            "compras:detalle_compra",
            compra_id=compra_id,
        )

    with transaction.atomic():

        compra = get_object_or_404(
            Compra.objects.select_for_update(),
            id=compra_id,
        )

        if compra.estado == Compra.EstadoCompra.ANULADA:
            messages.error(
                request,
                "La compra ya se encuentra anulada.",
            )

            return redirect(
                "compras:detalle_compra",
                compra_id=compra.id,
            )

        if compra.estado == Compra.EstadoCompra.CONFIRMADA:

            detalles = list(
                compra.detalles.select_related(
                    "producto",
                )
            )

            productos_bloqueados = {}

            for detalle in detalles:

                producto = Producto.objects.select_for_update().get(
                    id=detalle.producto_id,
                )

                if producto.stock_actual < detalle.cantidad:
                    messages.error(
                        request,
                        (
                            f'No se puede anular la compra porque '
                            f'el producto "{producto.nombre}" no tiene '
                            "stock suficiente para revertir la entrada."
                        ),
                    )

                    return redirect(
                        "compras:detalle_compra",
                        compra_id=compra.id,
                    )

                productos_bloqueados[producto.id] = producto

            for detalle in detalles:

                producto = productos_bloqueados[
                    detalle.producto_id
                ]

                stock_anterior = producto.stock_actual
                stock_posterior = (
                    stock_anterior
                    - detalle.cantidad
                )

                producto.stock_actual = stock_posterior

                ultimo_detalle_confirmado = (
                    producto.detalles_compra
                    .filter(
                        compra__estado=Compra.EstadoCompra.CONFIRMADA,
                    )
                    .exclude(
                        compra=compra,
                    )
                    .order_by(
                        F("compra__fecha_confirmacion").desc(
                            nulls_last=True,
                        ),
                        "-compra__fecha_compra",
                        "-compra__id",
                        "-id",
                    )
                    .first()
                )

                campos_actualizados = [
                    "stock_actual",
                    "precio_compra",
                    "fecha_modificacion",
                ]

                if ultimo_detalle_confirmado:
                    producto.precio_compra = (
                        ultimo_detalle_confirmado.costo_unitario
                    )

                    producto.precio_venta = (
                        ultimo_detalle_confirmado.precio_venta
                    )

                    campos_actualizados.append(
                        "precio_venta"
                    )
                else:
                    producto.precio_compra = Decimal("0.00")
                    producto.precio_venta = Decimal("0.00")

                    campos_actualizados.append(
                        "precio_venta"
                    )

                producto.save(
                    update_fields=campos_actualizados,
                )

                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo_movimiento=(
                        MovimientoInventario
                        .TipoMovimiento
                        .AJUSTE_SALIDA
                    ),
                    cantidad=detalle.cantidad,
                    stock_anterior=stock_anterior,
                    stock_posterior=stock_posterior,
                    compra=compra,
                    motivo=(
                        f"Anulación de la compra "
                        f"N.º {compra.id}"
                    ),
                    observaciones=(
                        "Reversión del ingreso generado "
                        "por la compra confirmada."
                    ),
                    usuario=request.user,
                )

        compra.estado = Compra.EstadoCompra.ANULADA
        compra.usuario_anulacion = request.user
        compra.fecha_anulacion = timezone.now()
        compra.motivo_anulacion = motivo_anulacion

        compra.save(
            update_fields=[
                "estado",
                "usuario_anulacion",
                "fecha_anulacion",
                "motivo_anulacion",
                "fecha_modificacion",
            ]
        )

        messages.success(
            request,
            (
                f"La compra N.º {compra.id} fue anulada "
                "correctamente."
            ),
        )

    return redirect(
        "compras:detalle_compra",
        compra_id=compra.id,
    )