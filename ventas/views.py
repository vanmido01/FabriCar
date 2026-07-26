from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from principal.decorators import rol_requerido
from .forms import DetalleVentaFormSet, VentaForm
from .models import Venta

from django.views.decorators.http import require_POST
from inventario.models import MovimientoInventario
from productos.models import Producto
from creditos.models import Credito


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_ventas(request):
    """Muestra las ventas con búsqueda, filtros y paginación."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    filtro_pago = request.GET.get(
        "forma_pago",
        "",
    ).strip()

    ventas = Venta.objects.select_related(
        "cliente",
        "usuario_registro",
    )

    if busqueda:
        ventas = ventas.filter(
            Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__documento__icontains=busqueda)
            | Q(numero_comprobante__icontains=busqueda)
            | Q(usuario_registro__username__icontains=busqueda)
        )

    if filtro_estado in Venta.EstadoVenta.values:
        ventas = ventas.filter(
            estado=filtro_estado,
        )

    if filtro_pago in Venta.FormaPago.values:
        ventas = ventas.filter(
            forma_pago=filtro_pago,
        )

    ventas = ventas.order_by(
        "-fecha_venta",
        "-id",
    )

    paginador = Paginator(
        ventas,
        10,
    )

    pagina_ventas = paginador.get_page(
        request.GET.get("pagina")
    )

    puede_gestionar_ventas = (
        request.user.is_superuser
        or request.user.groups.filter(
            name__in=[
                "Administrador",
                "Empleado",
            ]
        ).exists()
    )

    contexto = {
        "ventas": pagina_ventas,
        "pagina_ventas": pagina_ventas,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "filtro_pago": filtro_pago,
        "estados_venta": Venta.EstadoVenta.choices,
        "formas_pago": Venta.FormaPago.choices,
        "puede_gestionar_ventas": puede_gestionar_ventas,
    }

    return render(
        request,
        "ventas/listar_ventas.html",
        contexto,
    )


@login_required
@rol_requerido("Administrador", "Empleado")
def registrar_venta(request):
    """Registra una venta en estado borrador."""

    venta = Venta(
        usuario_registro=request.user,
        estado=Venta.EstadoVenta.BORRADOR,
    )

    if request.method == "POST":
        formulario = VentaForm(
            request.POST,
            instance=venta,
        )

        detalles_formset = DetalleVentaFormSet(
            request.POST,
            instance=venta,
        )

        if formulario.is_valid() and detalles_formset.is_valid():

            with transaction.atomic():
                venta = formulario.save(commit=False)

                venta.usuario_registro = request.user
                venta.estado = Venta.EstadoVenta.BORRADOR
                venta.save()

                detalles_formset.instance = venta
                detalles_formset.save()

                venta.actualizar_total()

            messages.success(
                request,
                (
                    f"La venta N.º {venta.id} fue registrada "
                    "correctamente en estado borrador."
                ),
            )

            return redirect(
                "ventas:listar_ventas"
            )

    else:
        formulario = VentaForm(
            instance=venta,
        )

        detalles_formset = DetalleVentaFormSet(
            instance=venta,
        )

    contexto = {
        "formulario": formulario,
        "detalles_formset": detalles_formset,
    }

    return render(
        request,
        "ventas/registrar_venta.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def detalle_venta(request, venta_id):
    """Muestra la información completa de una venta."""

    venta = get_object_or_404(
        Venta.objects
        .select_related(
            "cliente",
            "usuario_registro",
            "credito",
        )
        .prefetch_related(
            "detalles__producto",
        ),
        id=venta_id,
    )
    credito_relacionado = getattr(
        venta,
        "credito",
        None,
    )

    contexto = {
        "venta": venta,
        "credito_relacionado": credito_relacionado,
    }

    return render(
        request,
        "ventas/detalle_venta.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def editar_venta(request, venta_id):
    """Modifica una venta mientras se encuentra en borrador."""

    venta = get_object_or_404(
        Venta,
        id=venta_id,
    )

    if venta.estado != Venta.EstadoVenta.BORRADOR:
        messages.error(
            request,
            "Solo las ventas en estado borrador pueden ser modificadas.",
        )

        return redirect(
            "ventas:detalle_venta",
            venta_id=venta.id,
        )

    if request.method == "POST":
        formulario = VentaForm(
            request.POST,
            instance=venta,
        )

        detalles_formset = DetalleVentaFormSet(
            request.POST,
            instance=venta,
        )

        if formulario.is_valid() and detalles_formset.is_valid():

            with transaction.atomic():
                venta = formulario.save()

                detalles_formset.instance = venta
                detalles_formset.save()

                venta.actualizar_total()

            messages.success(
                request,
                (
                    f"La venta N.º {venta.id} fue "
                    "actualizada correctamente."
                ),
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )

    else:
        formulario = VentaForm(
            instance=venta,
        )

        detalles_formset = DetalleVentaFormSet(
            instance=venta,
        )

    contexto = {
        "venta": venta,
        "formulario": formulario,
        "detalles_formset": detalles_formset,
    }

    return render(
        request,
        "ventas/editar_venta.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
@require_POST
def confirmar_venta(request, venta_id):
    """Confirma una venta y descuenta sus productos del inventario."""

    with transaction.atomic():
        venta = get_object_or_404(
            Venta.objects.select_for_update(),
            id=venta_id,
        )

        if venta.estado != Venta.EstadoVenta.BORRADOR:
            messages.error(
                request,
                "Solo las ventas en estado borrador pueden confirmarse.",
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )

        detalles = list(
            venta.detalles
            .select_related("producto")
            .all()
        )

        if not detalles:
            messages.error(
                request,
                "La venta no puede confirmarse porque no contiene productos.",
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )

        productos_ids = [
            detalle.producto_id
            for detalle in detalles
        ]

        productos_bloqueados = {
            producto.id: producto
            for producto in (
                Producto.objects
                .select_for_update()
                .filter(id__in=productos_ids)
                .order_by("id")
            )
        }

        for detalle in detalles:
            producto = productos_bloqueados.get(
                detalle.producto_id
            )

            if producto is None or not producto.estado:
                messages.error(
                    request,
                    (
                        f'El producto "{detalle.producto.nombre}" '
                        "no está disponible."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

            if detalle.cantidad > producto.stock_actual:
                messages.error(
                    request,
                    (
                        f'Stock insuficiente para "{producto.nombre}". '
                        f"Disponible: {producto.stock_actual}; "
                        f"solicitado: {detalle.cantidad}."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

        for detalle in detalles:
            producto = productos_bloqueados[
                detalle.producto_id
            ]

            stock_anterior = producto.stock_actual
            stock_posterior = (
                stock_anterior - detalle.cantidad
            )

            producto.stock_actual = stock_posterior
            producto.save(
                update_fields=[
                    "stock_actual",
                    "fecha_modificacion",
                ]
            )

            MovimientoInventario.objects.create(
                producto=producto,
                tipo_movimiento=(
                    MovimientoInventario
                    .TipoMovimiento
                    .SALIDA_VENTA
                ),
                cantidad=detalle.cantidad,
                stock_anterior=stock_anterior,
                stock_posterior=stock_posterior,
                venta=venta,
                motivo=(
                    f"Confirmación de la venta N.º {venta.id}"
                ),
                observaciones=(
                    f"Comprobante: "
                    f"{venta.numero_comprobante or 'Sin número'}"
                ),
                usuario=request.user,
            )

        venta.estado = Venta.EstadoVenta.CONFIRMADA
        venta.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

    if venta.forma_pago == Venta.FormaPago.CREDITO:
        Credito.objects.get_or_create(
            venta=venta,
            defaults={
                "fecha_inicio": venta.fecha_venta,
                "monto_total": venta.total,
                "saldo_pendiente": venta.total,
                "estado": Credito.EstadoCredito.PENDIENTE,
                "observaciones": (
                    f"Crédito generado por la venta "
                    f"N.º {venta.id}."
                ),
                "usuario_registro": request.user,
        },
    )

    messages.success(
        request,
        (
            f"La venta N.º {venta.id} fue confirmada "
            "y el stock fue actualizado correctamente."
        ),
    )

    return redirect(
        "ventas:detalle_venta",
        venta_id=venta.id,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
@require_POST
def anular_venta(request, venta_id):
    """Anula una venta y repone el stock cuando estaba confirmada."""

    with transaction.atomic():
        venta = get_object_or_404(
            Venta.objects.select_for_update(),
            id=venta_id,
        )

        if venta.estado == Venta.EstadoVenta.ANULADA:
            messages.error(
                request,
                "La venta ya se encuentra anulada.",
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )

        estado_anterior = venta.estado
        credito = (
            Credito.objects
            .select_for_update()
            .filter(venta=venta)
            .first()
        )

        if credito and credito.pagos.exists():
            messages.error(
                request,
                (
                    "La venta no puede anularse porque su crédito "
                    "ya tiene pagos registrados."
                ),
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )        

        if estado_anterior == Venta.EstadoVenta.CONFIRMADA:
            detalles = list(
                venta.detalles
                .select_related("producto")
                .all()
            )

            productos_ids = [
                detalle.producto_id
                for detalle in detalles
            ]

            productos_bloqueados = {
                producto.id: producto
                for producto in (
                    Producto.objects
                    .select_for_update()
                    .filter(id__in=productos_ids)
                    .order_by("id")
                )
            }

            for detalle in detalles:
                producto = productos_bloqueados.get(
                    detalle.producto_id
                )

                if producto is None:
                    messages.error(
                        request,
                        (
                            "No fue posible reponer el stock del "
                            f'producto "{detalle.producto.nombre}".'
                        ),
                    )

                    return redirect(
                        "ventas:detalle_venta",
                        venta_id=venta.id,
                    )

                stock_anterior = producto.stock_actual
                stock_posterior = (
                    stock_anterior + detalle.cantidad
                )

                producto.stock_actual = stock_posterior
                producto.save(
                    update_fields=[
                        "stock_actual",
                        "fecha_modificacion",
                    ]
                )

                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo_movimiento=(
                        MovimientoInventario
                        .TipoMovimiento
                        .AJUSTE_ENTRADA
                    ),
                    cantidad=detalle.cantidad,
                    stock_anterior=stock_anterior,
                    stock_posterior=stock_posterior,
                    venta=venta,
                    motivo=(
                        f"Anulación de la venta N.º {venta.id}"
                    ),
                    observaciones=(
                        "Reversión de salida por venta. "
                        f"Comprobante: "
                        f"{venta.numero_comprobante or 'Sin número'}"
                    ),
                    usuario=request.user,
                )

        venta.estado = Venta.EstadoVenta.ANULADA
        venta.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        if credito:
            credito.estado = Credito.EstadoCredito.ANULADO
            credito.saldo_pendiente = 0

            credito.save(
                update_fields=[
                    "estado",
                    "saldo_pendiente",
                    "fecha_modificacion",
                ]
            )

    if estado_anterior == Venta.EstadoVenta.CONFIRMADA:
        messages.success(
            request,
            (
                f"La venta N.º {venta.id} fue anulada "
                "y el stock fue repuesto correctamente."
            ),
        )
    else:
        messages.success(
            request,
            f"La venta N.º {venta.id} fue anulada correctamente.",
        )

    return redirect(
        "ventas:detalle_venta",
        venta_id=venta.id,
    )