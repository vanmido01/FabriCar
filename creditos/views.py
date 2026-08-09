from decimal import Decimal
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as ReportLabImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from principal.decorators import rol_requerido
from reportes.models import ConfiguracionReportes

from .forms import CreditoForm, PagoCreditoForm
from .models import Credito, PagoCredito


def texto_seguro_pdf(
    valor,
    valor_vacio="No registrado",
):
    """Prepara texto seguro para los párrafos de ReportLab."""

    if valor is None:
        return valor_vacio

    texto = str(valor).strip()

    if not texto:
        return valor_vacio

    return (
        escape(texto)
        .replace("\n", "<br/>")
    )


def fecha_hora_pdf(valor):
    """Convierte una fecha y hora a la zona horaria local."""

    if not valor:
        return "No registrada"

    try:
        valor = timezone.localtime(valor)
    except (ValueError, TypeError):
        pass

    return valor.strftime(
        "%d/%m/%Y %H:%M"
    )


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
            Q(
                venta__codigo_venta__icontains=busqueda
            )
            | Q(
                venta__cliente__nombre__icontains=busqueda
            )
            | Q(
                venta__cliente__documento__icontains=busqueda
            )
            | Q(
                venta__numero_comprobante__icontains=busqueda
            )
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
        "-fecha_inicio",
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
def comprobante_pago_pdf(request, pago_id):
    """Genera el comprobante PDF individual de un pago."""

    pago = get_object_or_404(
        PagoCredito.objects
        .select_related(
            "credito",
            "credito__venta",
            "credito__venta__cliente",
            "usuario_registro",
        ),
        id=pago_id,
    )

    credito = pago.credito
    venta = credito.venta

    codigo_recibo = (
        f"REC-{pago.fecha_pago.year}-"
        f"{pago.id:06d}"
    )

    configuracion = (
        ConfiguracionReportes.objects.first()
    )

    ruta_logo = None

    if configuracion and configuracion.logo:
        try:
            ruta_logo = configuracion.logo.path
        except (ValueError, OSError):
            ruta_logo = None

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{codigo_recibo}.pdf"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title=(
            f"Comprobante de pago "
            f"{codigo_recibo}"
        ),
        author="FABRI-CAR",
    )

    estilos_base = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )

    estilo_codigo = ParagraphStyle(
        "CodigoComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_normal = ParagraphStyle(
        "NormalComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    estilo_etiqueta = ParagraphStyle(
        "EtiquetaComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    estilo_monto = ParagraphStyle(
        "MontoComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#166534"),
    )

    estilo_monto_etiqueta = ParagraphStyle(
        "MontoEtiquetaComprobantePago",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
    )

    estilo_derecha = ParagraphStyle(
        "DerechaComprobantePago",
        parent=estilo_normal,
        alignment=TA_RIGHT,
    )

    elementos = []

    # ---------------------------------------------------------
    # Logotipo
    # ---------------------------------------------------------

    logo_pdf = ""

    if ruta_logo:
        try:
            lector_logo = ImageReader(
                ruta_logo
            )

            ancho_original, alto_original = (
                lector_logo.getSize()
            )

            alto_logo = 1.5 * cm

            ancho_logo = (
                alto_logo
                * ancho_original
                / alto_original
            )

            if ancho_logo > 3.1 * cm:
                ancho_logo = 3.1 * cm

                alto_logo = (
                    ancho_logo
                    * alto_original
                    / ancho_original
                )

            logo_pdf = ReportLabImage(
                ruta_logo,
                width=ancho_logo,
                height=alto_logo,
            )

        except (
            OSError,
            ValueError,
            TypeError,
            ZeroDivisionError,
        ):
            logo_pdf = ""

    # ---------------------------------------------------------
    # Encabezado
    # ---------------------------------------------------------

    encabezado_central = [
        Paragraph(
            "COMPROBANTE DE PAGO",
            estilo_titulo,
        ),
        Paragraph(
            "Crédito y cuenta por cobrar",
            estilo_subtitulo,
        ),
    ]

    encabezado_derecho = [
        Paragraph(
            codigo_recibo,
            estilo_codigo,
        ),
        Paragraph(
            (
                "Fecha de pago: "
                f"{pago.fecha_pago.strftime('%d/%m/%Y')}"
            ),
            estilo_derecha,
        ),
    ]

    tabla_encabezado = Table(
        [
            [
                logo_pdf,
                encabezado_central,
                encabezado_derecho,
            ]
        ],
        colWidths=[
            3.7 * cm,
            8.3 * cm,
            6 * cm,
        ],
    )

    tabla_encabezado.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (2, 0),
                    (2, 0),
                    "RIGHT",
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    1,
                    colors.HexColor("#94a3b8"),
                ),
            ]
        )
    )

    elementos.append(
        tabla_encabezado
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    # ---------------------------------------------------------
    # Datos principales
    # ---------------------------------------------------------

    referencia_venta = (
        venta.codigo_venta
        or f"Venta N.º {venta.id}"
    )

    datos_generales = [
        [
            Paragraph(
                "Cliente",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.nombre_cliente_mostrado
                ),
                estilo_normal,
            ),
            Paragraph(
                "NIT o C.I.",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.documento_cliente_mostrado
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Venta relacionada",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    referencia_venta
                ),
                estilo_normal,
            ),
            Paragraph(
                "Crédito",
                estilo_etiqueta,
            ),
            Paragraph(
                f"Crédito N.º {credito.id}",
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Método de pago",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    pago.get_metodo_pago_display()
                ),
                estilo_normal,
            ),
            Paragraph(
                "Referencia",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    pago.referencia
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Registrado por",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    (
                        pago.usuario_registro.get_username()
                        if pago.usuario_registro
                        else ""
                    )
                ),
                estilo_normal,
            ),
            Paragraph(
                "Fecha de registro",
                estilo_etiqueta,
            ),
            Paragraph(
                fecha_hora_pdf(
                    pago.fecha_registro
                ),
                estilo_normal,
            ),
        ],
    ]

    tabla_datos = Table(
        datos_generales,
        colWidths=[
            3.2 * cm,
            5.8 * cm,
            3.2 * cm,
            5.8 * cm,
        ],
    )

    tabla_datos.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elementos.append(
        tabla_datos
    )

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    # ---------------------------------------------------------
    # Monto recibido
    # ---------------------------------------------------------

    tabla_monto = Table(
        [
            [
                Paragraph(
                    "MONTO RECIBIDO",
                    estilo_monto_etiqueta,
                ),
            ],
            [
                Paragraph(
                    f"Bs {pago.monto:.2f}",
                    estilo_monto,
                ),
            ],
        ],
        colWidths=[
            18 * cm,
        ],
    )

    tabla_monto.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f0fdf4"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1,
                    colors.HexColor("#86efac"),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    elementos.append(
        tabla_monto
    )

    elementos.append(
        Spacer(
            1,
            0.35 * cm,
        )
    )

    # ---------------------------------------------------------
    # Resumen del crédito
    # ---------------------------------------------------------

    resumen_credito = [
        [
            Paragraph(
                "Monto total del crédito",
                estilo_etiqueta,
            ),
            Paragraph(
                f"Bs {credito.monto_total:.2f}",
                estilo_derecha,
            ),
        ],
        [
            Paragraph(
                "Pago registrado",
                estilo_etiqueta,
            ),
            Paragraph(
                f"Bs {pago.monto:.2f}",
                estilo_derecha,
            ),
        ],
        [
            Paragraph(
                "Saldo pendiente actual",
                estilo_etiqueta,
            ),
            Paragraph(
                f"Bs {credito.saldo_pendiente:.2f}",
                estilo_derecha,
            ),
        ],
        [
            Paragraph(
                "Estado actual",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    credito.get_estado_display()
                ),
                estilo_derecha,
            ),
        ],
    ]

    tabla_resumen = Table(
        resumen_credito,
        colWidths=[
            11 * cm,
            7 * cm,
        ],
    )

    tabla_resumen.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#f8fafc"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elementos.append(
        tabla_resumen
    )

    # ---------------------------------------------------------
    # Observaciones
    # ---------------------------------------------------------

    if pago.observaciones:
        elementos.append(
            Spacer(
                1,
                0.4 * cm,
            )
        )

        tabla_observaciones = Table(
            [
                [
                    Paragraph(
                        "Observaciones",
                        estilo_etiqueta,
                    ),
                ],
                [
                    Paragraph(
                        texto_seguro_pdf(
                            pago.observaciones
                        ),
                        estilo_normal,
                    ),
                ],
            ],
            colWidths=[
                18 * cm,
            ],
        )

        tabla_observaciones.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#f8fafc"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#cbd5e1"),
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                ]
            )
        )

        elementos.append(
            tabla_observaciones
        )

    # ---------------------------------------------------------
    # Espacio de constancia
    # ---------------------------------------------------------

    elementos.append(
        Spacer(
            1,
            1.2 * cm,
        )
    )

    tabla_firmas = Table(
        [
            [
                Paragraph(
                    "______________________________",
                    estilo_normal,
                ),
                Paragraph(
                    "______________________________",
                    estilo_normal,
                ),
            ],
            [
                Paragraph(
                    "Entregado por FABRI-CAR",
                    estilo_normal,
                ),
                Paragraph(
                    "Recibí conforme",
                    estilo_normal,
                ),
            ],
        ],
        colWidths=[
            9 * cm,
            9 * cm,
        ],
    )

    tabla_firmas.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    elementos.append(
        tabla_firmas
    )

    # ---------------------------------------------------------
    # Pie de página
    # ---------------------------------------------------------

    def decorar_pagina(
        canvas,
        documento_pdf,
    ):
        canvas.saveState()

        ancho_pagina, _ = A4

        canvas.setStrokeColor(
            colors.HexColor("#cbd5e1")
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            1.5 * cm,
            1.05 * cm,
            ancho_pagina - 1.5 * cm,
            1.05 * cm,
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.setFillColor(
            colors.HexColor("#64748b")
        )

        canvas.drawString(
            1.5 * cm,
            0.68 * cm,
            (
                "Comprobante generado automáticamente "
                "por FABRI-CAR"
            ),
        )

        canvas.drawRightString(
            ancho_pagina - 1.5 * cm,
            0.68 * cm,
            f"Página {documento_pdf.page}",
        )

        canvas.restoreState()

    documento.build(
        elementos,
        onFirstPage=decorar_pagina,
        onLaterPages=decorar_pagina,
    )

    return response

@login_required
@rol_requerido("Administrador", "Empleado")
def estado_cuenta_credito_pdf(request, credito_id):
    """
    Genera un estado de cuenta completo con todos los pagos
    registrados y el saldo actual del crédito.
    """

    credito = get_object_or_404(
        Credito.objects
        .select_related(
            "venta",
            "venta__cliente",
            "usuario_registro",
        ),
        id=credito_id,
    )

    venta = credito.venta

    pagos = list(
        credito.pagos
        .select_related(
            "usuario_registro",
        )
        .order_by(
            "fecha_pago",
            "id",
        )
    )

    total_pagado = sum(
        (
            pago.monto
            for pago in pagos
        ),
        Decimal("0.00"),
    )

    configuracion = (
        ConfiguracionReportes.objects.first()
    )

    ruta_logo = None

    if configuracion and configuracion.logo:
        try:
            ruta_logo = configuracion.logo.path
        except (ValueError, OSError):
            ruta_logo = None

    nombre_archivo = (
        f"ESTADO-CREDITO-{credito.id:06d}.pdf"
    )

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{nombre_archivo}"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.5 * cm,
        title=(
            f"Estado de cuenta del crédito "
            f"N.º {credito.id}"
        ),
        author="FABRI-CAR",
    )

    estilos_base = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle(
        "TituloEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
    )

    estilo_codigo = ParagraphStyle(
        "CodigoEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_normal = ParagraphStyle(
        "NormalEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    estilo_etiqueta = ParagraphStyle(
        "EtiquetaEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    estilo_celda = ParagraphStyle(
        "CeldaEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    estilo_celda_centro = ParagraphStyle(
        "CeldaCentroEstadoCuentaCredito",
        parent=estilo_celda,
        alignment=TA_CENTER,
    )

    estilo_celda_derecha = ParagraphStyle(
        "CeldaDerechaEstadoCuentaCredito",
        parent=estilo_celda,
        alignment=TA_RIGHT,
    )

    estilo_cabecera = ParagraphStyle(
        "CabeceraEstadoCuentaCredito",
        parent=estilo_celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    estilo_cabecera_centro = ParagraphStyle(
        "CabeceraCentroEstadoCuentaCredito",
        parent=estilo_cabecera,
        alignment=TA_CENTER,
    )

    estilo_cabecera_derecha = ParagraphStyle(
        "CabeceraDerechaEstadoCuentaCredito",
        parent=estilo_cabecera,
        alignment=TA_RIGHT,
    )

    estilo_resumen = ParagraphStyle(
        "ResumenEstadoCuentaCredito",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_resumen_derecha = ParagraphStyle(
        "ResumenDerechaEstadoCuentaCredito",
        parent=estilo_resumen,
        alignment=TA_RIGHT,
    )

    elementos = []

    # ---------------------------------------------------------
    # Logotipo
    # ---------------------------------------------------------

    logo_pdf = ""

    if ruta_logo:
        try:
            lector_logo = ImageReader(
                ruta_logo
            )

            ancho_original, alto_original = (
                lector_logo.getSize()
            )

            alto_logo = 1.5 * cm

            ancho_logo = (
                alto_logo
                * ancho_original
                / alto_original
            )

            if ancho_logo > 3.1 * cm:
                ancho_logo = 3.1 * cm

                alto_logo = (
                    ancho_logo
                    * alto_original
                    / ancho_original
                )

            logo_pdf = ReportLabImage(
                ruta_logo,
                width=ancho_logo,
                height=alto_logo,
            )

        except (
            OSError,
            ValueError,
            TypeError,
            ZeroDivisionError,
        ):
            logo_pdf = ""

    # ---------------------------------------------------------
    # Encabezado
    # ---------------------------------------------------------

    encabezado_central = [
        Paragraph(
            "ESTADO DE CUENTA",
            estilo_titulo,
        ),
        Paragraph(
            "Crédito y cuenta por cobrar",
            estilo_subtitulo,
        ),
    ]

    referencia_venta = (
        venta.codigo_venta
        or f"Venta N.º {venta.id}"
    )

    encabezado_derecho = [
        Paragraph(
            f"CRÉDITO N.º {credito.id}",
            estilo_codigo,
        ),
        Paragraph(
            texto_seguro_pdf(
                referencia_venta
            ),
            estilo_celda_derecha,
        ),
    ]

    tabla_encabezado = Table(
        [
            [
                logo_pdf,
                encabezado_central,
                encabezado_derecho,
            ]
        ],
        colWidths=[
            3.7 * cm,
            8.3 * cm,
            6 * cm,
        ],
    )

    tabla_encabezado.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (2, 0),
                    (2, 0),
                    "RIGHT",
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    1,
                    colors.HexColor("#94a3b8"),
                ),
            ]
        )
    )

    elementos.append(
        tabla_encabezado
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    # ---------------------------------------------------------
    # Situación del crédito
    # ---------------------------------------------------------

    if credito.estado == Credito.EstadoCredito.PAGADO:
        situacion = "Cancelado"

    elif credito.estado == Credito.EstadoCredito.ANULADO:
        situacion = "Sin vigencia"

    elif credito.esta_vencido:
        situacion = "Vencido"

    else:
        situacion = "Vigente"

    datos_generales = [
        [
            Paragraph(
                "Cliente",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.nombre_cliente_mostrado
                ),
                estilo_normal,
            ),
            Paragraph(
                "NIT o C.I.",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.documento_cliente_mostrado
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Venta relacionada",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    referencia_venta
                ),
                estilo_normal,
            ),
            Paragraph(
                "Forma de pago",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.get_forma_pago_display()
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Fecha de inicio",
                estilo_etiqueta,
            ),
            Paragraph(
                credito.fecha_inicio.strftime(
                    "%d/%m/%Y"
                ),
                estilo_normal,
            ),
            Paragraph(
                "Fecha de vencimiento",
                estilo_etiqueta,
            ),
            Paragraph(
                credito.fecha_vencimiento.strftime(
                    "%d/%m/%Y"
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Estado",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    credito.get_estado_display()
                ),
                estilo_normal,
            ),
            Paragraph(
                "Situación",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    situacion
                ),
                estilo_normal,
            ),
        ],
    ]

    tabla_datos = Table(
        datos_generales,
        colWidths=[
            3.2 * cm,
            5.8 * cm,
            3.2 * cm,
            5.8 * cm,
        ],
    )

    tabla_datos.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elementos.append(
        tabla_datos
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    # ---------------------------------------------------------
    # Resumen económico
    # ---------------------------------------------------------

    resumen = [
        [
            Paragraph(
                "MONTO TOTAL",
                estilo_resumen,
            ),
            Paragraph(
                "TOTAL PAGADO",
                estilo_resumen,
            ),
            Paragraph(
                "SALDO PENDIENTE",
                estilo_resumen,
            ),
        ],
        [
            Paragraph(
                f"Bs {credito.monto_total:.2f}",
                estilo_resumen_derecha,
            ),
            Paragraph(
                f"Bs {total_pagado:.2f}",
                estilo_resumen_derecha,
            ),
            Paragraph(
                f"Bs {credito.saldo_pendiente:.2f}",
                estilo_resumen_derecha,
            ),
        ],
    ]

    tabla_resumen = Table(
        resumen,
        colWidths=[
            6 * cm,
            6 * cm,
            6 * cm,
        ],
    )

    tabla_resumen.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "BACKGROUND",
                    (0, 1),
                    (-1, 1),
                    colors.HexColor("#f8fafc"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#94a3b8"),
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, 0),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    elementos.append(
        tabla_resumen
    )

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    # ---------------------------------------------------------
    # Historial de pagos
    # ---------------------------------------------------------

    datos_pagos = [
        [
            Paragraph(
                "N.º",
                estilo_cabecera_centro,
            ),
            Paragraph(
                "Fecha",
                estilo_cabecera_centro,
            ),
            Paragraph(
                "Comprobante",
                estilo_cabecera,
            ),
            Paragraph(
                "Método",
                estilo_cabecera,
            ),
            Paragraph(
                "Referencia",
                estilo_cabecera,
            ),
            Paragraph(
                "Abono",
                estilo_cabecera_derecha,
            ),
            Paragraph(
                "Saldo",
                estilo_cabecera_derecha,
            ),
        ]
    ]

    saldo_calculado = credito.monto_total

    for numero, pago in enumerate(
        pagos,
        start=1,
    ):
        saldo_calculado -= pago.monto

        if saldo_calculado < Decimal("0.00"):
            saldo_calculado = Decimal("0.00")

        codigo_recibo = (
            f"REC-{pago.fecha_pago.year}-"
            f"{pago.id:06d}"
        )

        datos_pagos.append(
            [
                Paragraph(
                    str(numero),
                    estilo_celda_centro,
                ),
                Paragraph(
                    pago.fecha_pago.strftime(
                        "%d/%m/%Y"
                    ),
                    estilo_celda_centro,
                ),
                Paragraph(
                    codigo_recibo,
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro_pdf(
                        pago.get_metodo_pago_display()
                    ),
                    estilo_celda,
                ),
                Paragraph(
                    texto_seguro_pdf(
                        pago.referencia,
                        "Sin referencia",
                    ),
                    estilo_celda,
                ),
                Paragraph(
                    f"Bs {pago.monto:.2f}",
                    estilo_celda_derecha,
                ),
                Paragraph(
                    f"Bs {saldo_calculado:.2f}",
                    estilo_celda_derecha,
                ),
            ]
        )

    if not pagos:
        datos_pagos.append(
            [
                Paragraph(
                    "No existen pagos registrados.",
                    estilo_celda_centro,
                ),
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    tabla_pagos = Table(
        datos_pagos,
        colWidths=[
            0.8 * cm,
            2.2 * cm,
            3.2 * cm,
            2.7 * cm,
            3.5 * cm,
            2.8 * cm,
            2.8 * cm,
        ],
        repeatRows=1,
    )

    estilo_tabla_pagos = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#1f2937"),
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.HexColor("#94a3b8"),
        ),
        (
            "ROWBACKGROUNDS",
            (0, 1),
            (-1, -1),
            [
                colors.white,
                colors.HexColor("#f8fafc"),
            ],
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "MIDDLE",
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            5,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            6,
        ),
    ]

    if not pagos:
        estilo_tabla_pagos.append(
            (
                "SPAN",
                (0, 1),
                (-1, 1),
            )
        )

    tabla_pagos.setStyle(
        TableStyle(
            estilo_tabla_pagos
        )
    )

    elementos.append(
        Paragraph(
            "Historial de pagos",
            estilo_resumen,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.15 * cm,
        )
    )

    elementos.append(
        tabla_pagos
    )

    # ---------------------------------------------------------
    # Observaciones del crédito
    # ---------------------------------------------------------

    if credito.observaciones:
        elementos.append(
            Spacer(
                1,
                0.4 * cm,
            )
        )

        tabla_observaciones = Table(
            [
                [
                    Paragraph(
                        "Observaciones",
                        estilo_etiqueta,
                    ),
                ],
                [
                    Paragraph(
                        texto_seguro_pdf(
                            credito.observaciones
                        ),
                        estilo_normal,
                    ),
                ],
            ],
            colWidths=[
                18 * cm,
            ],
        )

        tabla_observaciones.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#f8fafc"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#cbd5e1"),
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                ]
            )
        )

        elementos.append(
            tabla_observaciones
        )

    # ---------------------------------------------------------
    # Auditoría
    # ---------------------------------------------------------

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    auditoria = Table(
        [
            [
                Paragraph(
                    "Crédito registrado por",
                    estilo_etiqueta,
                ),
                Paragraph(
                    texto_seguro_pdf(
                        (
                            credito.usuario_registro.get_username()
                            if credito.usuario_registro
                            else ""
                        )
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    "Fecha de registro",
                    estilo_etiqueta,
                ),
                Paragraph(
                    fecha_hora_pdf(
                        credito.fecha_registro
                    ),
                    estilo_normal,
                ),
            ],
        ],
        colWidths=[
            3.2 * cm,
            5.8 * cm,
            3.2 * cm,
            5.8 * cm,
        ],
    )

    auditoria.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    colors.HexColor("#f1f5f9"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    elementos.append(
        auditoria
    )

    # ---------------------------------------------------------
    # Pie de página
    # ---------------------------------------------------------

    def decorar_pagina(
        canvas,
        documento_pdf,
    ):
        canvas.saveState()

        ancho_pagina, _ = A4

        canvas.setStrokeColor(
            colors.HexColor("#cbd5e1")
        )

        canvas.setLineWidth(
            0.5
        )

        canvas.line(
            1.5 * cm,
            1.05 * cm,
            ancho_pagina - 1.5 * cm,
            1.05 * cm,
        )

        canvas.setFont(
            "Helvetica",
            7.5,
        )

        canvas.setFillColor(
            colors.HexColor("#64748b")
        )

        canvas.drawString(
            1.5 * cm,
            0.68 * cm,
            (
                "Estado de cuenta generado automáticamente "
                "por FABRI-CAR"
            ),
        )

        canvas.drawRightString(
            ancho_pagina - 1.5 * cm,
            0.68 * cm,
            f"Página {documento_pdf.page}",
        )

        canvas.restoreState()

    documento.build(
        elementos,
        onFirstPage=decorar_pagina,
        onLaterPages=decorar_pagina,
    )

    return response

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