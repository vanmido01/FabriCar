from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from principal.decorators import rol_requerido

from .models import Credito
from django.contrib import messages
from django.db import transaction
from .forms import CreditoForm, PagoCreditoForm


@login_required
@rol_requerido("Administrador", "Empleado")
def listar_creditos(request):
    """Muestra las cuentas por cobrar con búsqueda y filtros."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    filtro_vencimiento = request.GET.get(
        "vencimiento",
        "",
    ).strip()

    creditos = (
        Credito.objects
        .select_related(
            "venta",
            "venta__cliente",
            "usuario_registro",
        )
    )

    if busqueda:
        creditos = creditos.filter(
            Q(venta__cliente__nombre__icontains=busqueda)
            | Q(venta__cliente__documento__icontains=busqueda)
            | Q(venta__numero_comprobante__icontains=busqueda)
        )

    if filtro_estado in Credito.EstadoCredito.values:
        creditos = creditos.filter(
            estado=filtro_estado,
        )

    if filtro_vencimiento == "VENCIDO":
        creditos = creditos.filter(
            fecha_vencimiento__lt=timezone.localdate(),
            saldo_pendiente__gt=0,
        ).exclude(
            estado__in=[
                Credito.EstadoCredito.PAGADO,
                Credito.EstadoCredito.ANULADO,
            ]
        )

    elif filtro_vencimiento == "VIGENTE":
        creditos = creditos.filter(
            fecha_vencimiento__gte=timezone.localdate(),
            saldo_pendiente__gt=0,
        ).exclude(
            estado__in=[
                Credito.EstadoCredito.PAGADO,
                Credito.EstadoCredito.ANULADO,
            ]
        )

    creditos = creditos.order_by(
        "fecha_vencimiento",
        "-id",
    )

    paginador = Paginator(
        creditos,
        10,
    )

    pagina_creditos = paginador.get_page(
        request.GET.get("pagina")
    )

    puede_gestionar_creditos = (
        request.user.is_superuser
        or request.user.groups.filter(
            name__in=[
                "Administrador",
                "Empleado",
            ]
        ).exists()
    )

    contexto = {
        "creditos": pagina_creditos,
        "pagina_creditos": pagina_creditos,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "filtro_vencimiento": filtro_vencimiento,
        "estados_credito": Credito.EstadoCredito.choices,
        "puede_gestionar_creditos": puede_gestionar_creditos,
    }

    return render(
        request,
        "creditos/listar_creditos.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def detalle_credito(request, credito_id):
    """Muestra la información completa de una cuenta por cobrar."""

    credito = get_object_or_404(
        Credito.objects
        .select_related(
            "venta",
            "venta__cliente",
            "usuario_registro",
        )
        .prefetch_related(
            "pagos",
            "pagos__usuario_registro",
        ),
        id=credito_id,
    )

    contexto = {
        "credito": credito,
    }

    return render(
        request,
        "creditos/detalle_credito.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def registrar_pago(request, credito_id):
    """Registra un pago y actualiza el saldo del crédito."""

    credito = get_object_or_404(
        Credito.objects.select_related(
            "venta",
            "venta__cliente",
        ),
        id=credito_id,
    )

    if credito.estado == Credito.EstadoCredito.ANULADO:
        messages.error(
            request,
            "No se pueden registrar pagos en un crédito anulado.",
        )

        return redirect(
            "creditos:detalle_credito",
            credito_id=credito.id,
        )

    if (
        credito.estado == Credito.EstadoCredito.PAGADO
        or credito.saldo_pendiente <= 0
    ):
        messages.error(
            request,
            "El crédito ya se encuentra completamente pagado.",
        )

        return redirect(
            "creditos:detalle_credito",
            credito_id=credito.id,
        )

    if request.method == "POST":

        with transaction.atomic():
            credito = get_object_or_404(
                Credito.objects
                .select_for_update()
                .select_related(
                    "venta",
                    "venta__cliente",
                ),
                id=credito_id,
            )

            formulario = PagoCreditoForm(
                request.POST,
                credito=credito,
            )

            if formulario.is_valid():
                pago = formulario.save(
                    commit=False,
                )

                pago.credito = credito
                pago.usuario_registro = request.user
                pago.save()

                messages.success(
                    request,
                    (
                        f"El pago de Bs {pago.monto} fue "
                        "registrado correctamente."
                    ),
                )

                return redirect(
                    "creditos:detalle_credito",
                    credito_id=credito.id,
                )

    else:
        formulario = PagoCreditoForm(
            credito=credito,
        )

    contexto = {
        "credito": credito,
        "formulario": formulario,
    }

    return render(
        request,
        "creditos/registrar_pago.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def editar_credito(request, credito_id):
    """Modifica el vencimiento y las observaciones de un crédito."""

    credito = get_object_or_404(
        Credito.objects.select_related(
            "venta",
            "venta__cliente",
        ),
        id=credito_id,
    )

    if credito.estado == Credito.EstadoCredito.ANULADO:
        messages.error(
            request,
            "No se puede modificar un crédito anulado.",
        )

        return redirect(
            "creditos:detalle_credito",
            credito_id=credito.id,
        )

    if credito.estado == Credito.EstadoCredito.PAGADO:
        messages.error(
            request,
            "No se puede modificar un crédito completamente pagado.",
        )

        return redirect(
            "creditos:detalle_credito",
            credito_id=credito.id,
        )

    if request.method == "POST":
        formulario = CreditoForm(
            request.POST,
            instance=credito,
        )

        if formulario.is_valid():
            formulario.save()

            messages.success(
                request,
                (
                    f"Las condiciones del crédito N.º "
                    f"{credito.id} fueron actualizadas."
                ),
            )

            return redirect(
                "creditos:detalle_credito",
                credito_id=credito.id,
            )

    else:
        formulario = CreditoForm(
            instance=credito,
        )

    contexto = {
        "credito": credito,
        "formulario": formulario,
    }

    return render(
        request,
        "creditos/editar_credito.html",
        contexto,
    )