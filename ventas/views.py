from decimal import Decimal
from xml.sax.saxutils import escape
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import (
    Case,
    IntegerField,
    Q,
    Value,
    When,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.utils import timezone

from principal.decorators import rol_requerido
from .forms import DetalleVentaFormSet, VentaForm
from .models import SecuenciaVenta, Venta

from django.views.decorators.http import (
    require_GET,
    require_POST,
)
from creditos.models import Credito, PagoCredito
from inventario.models import MovimientoInventario
from productos.models import Producto
from reportes.models import ConfiguracionReportes

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


def obtener_datos_productos_venta():
    """
    Devuelve stock y precio vigente de los productos disponibles.
    """

    productos = (
        Producto.objects
        .filter(
            estado=True,
            stock_actual__gt=0,
        )
        .values(
            "id",
            "stock_actual",
            "precio_venta",
        )
    )

    return {
        str(producto["id"]): {
            "stock": producto["stock_actual"],
            "precio_venta": str(
                producto["precio_venta"]
            ),
        }
        for producto in productos
    }

def calcular_total_formset_venta(
    detalles_formset,
):
    """
    Calcula el total de los productos válidos del formset.

    No toma en cuenta las filas vacías ni las marcadas
    para eliminar.
    """

    total = Decimal("0.00")

    for formulario_detalle in detalles_formset.forms:

        datos = getattr(
            formulario_detalle,
            "cleaned_data",
            {},
        )

        if not datos:
            continue

        if datos.get("DELETE"):
            continue

        producto = datos.get("producto")
        cantidad = datos.get("cantidad")
        precio_unitario = datos.get(
            "precio_unitario"
        )

        if (
            producto is None
            or cantidad is None
            or precio_unitario is None
        ):
            continue

        total += (
            Decimal(cantidad)
            * precio_unitario
        )

    return total

def validar_pago_inicial_venta(
    formulario,
    detalles_formset,
):
    """
    Comprueba que el pago inicial no sea mayor
    al total de los productos de la venta.
    """

    forma_pago = formulario.cleaned_data.get(
        "forma_pago"
    )

    if forma_pago != Venta.FormaPago.CREDITO:
        return True

    monto_pago_inicial = (
        formulario.cleaned_data.get(
            "monto_pago_inicial"
        )
        or Decimal("0.00")
    )

    total_venta = calcular_total_formset_venta(
        detalles_formset
    )

    if monto_pago_inicial > total_venta:
        formulario.add_error(
            "monto_pago_inicial",
            (
                "El pago inicial no puede superar "
                f"el total de la venta de "
                f"Bs {total_venta:.2f}."
            ),
        )

        return False

    return True

def generar_codigo_venta(venta):
    """
    Genera un código consecutivo y único para una venta confirmada.

    Debe ejecutarse dentro de transaction.atomic().
    """

    if venta.codigo_venta:
        return venta.codigo_venta

    gestion = venta.fecha_venta.year

    secuencia, creada = (
        SecuenciaVenta.objects
        .select_for_update()
        .get_or_create(
            gestion=gestion,
            defaults={
                "ultimo_numero": 0,
            },
        )
    )

    secuencia.ultimo_numero += 1

    secuencia.save(
        update_fields=[
            "ultimo_numero",
            "fecha_modificacion",
        ]
    )

    return (
        f"VTA-{gestion}-"
        f"{secuencia.ultimo_numero:06d}"
    )

def texto_seguro_pdf(valor, valor_vacio="No registrado"):
    """
    Convierte un valor en texto seguro para Paragraph de ReportLab.
    """

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
    """Formatea una fecha y hora utilizando la zona horaria local."""

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
@require_GET
def buscar_productos_venta(request):
    """
    Busca productos disponibles para una venta.

    Prioriza el código del producto y devuelve como máximo
    15 resultados para mantener la búsqueda rápida.
    """

    producto_id = request.GET.get(
        "id",
        "",
    ).strip()

    # ---------------------------------------------------------
    # Consulta exacta por ID.
    # Se utiliza principalmente al editar una venta existente.
    # ---------------------------------------------------------

    if producto_id:
        try:
            producto_id = int(
                producto_id
            )
        except (TypeError, ValueError):
            return JsonResponse(
                {
                    "resultados": [],
                }
            )

        producto = (
            Producto.objects
            .filter(
                id=producto_id,
                estado=True,
            )
            .first()
        )

        if producto is None:
            return JsonResponse(
                {
                    "resultados": [],
                }
            )

        return JsonResponse(
            {
                "resultados": [
                    {
                        "id": producto.id,
                        "codigo": producto.codigo,
                        "nombre": producto.nombre,
                        "marca": (
                            producto.marca
                            or ""
                        ),
                        "stock": (
                            producto.stock_actual
                        ),
                        "precio_venta": str(
                            producto.precio_venta
                        ),
                    }
                ],
            }
        )

    # ---------------------------------------------------------
    # Búsqueda normal.
    # ---------------------------------------------------------

    termino = request.GET.get(
        "q",
        "",
    ).strip()

    if not termino:
        return JsonResponse(
            {
                "resultados": [],
            }
        )

    # Evita búsquedas excesivamente largas.
    termino = termino[:80]

    palabras = [
        palabra
        for palabra in termino.split()
        if palabra
    ]

    productos = Producto.objects.filter(
        estado=True,
        stock_actual__gt=0,
    )

    # Cada palabra debe aparecer en código, nombre o marca.
    for palabra in palabras:
        productos = productos.filter(
            Q(
                codigo__icontains=palabra
            )
            | Q(
                nombre__icontains=palabra
            )
            | Q(
                marca__icontains=palabra
            )
        )

    productos = (
        productos
        .annotate(
            prioridad_busqueda=Case(
                When(
                    codigo__iexact=termino,
                    then=Value(0),
                ),
                When(
                    codigo__istartswith=termino,
                    then=Value(1),
                ),
                When(
                    codigo__icontains=termino,
                    then=Value(2),
                ),
                When(
                    nombre__istartswith=termino,
                    then=Value(3),
                ),
                When(
                    nombre__icontains=termino,
                    then=Value(4),
                ),
                default=Value(5),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "prioridad_busqueda",
            "codigo",
            "nombre",
        )[:15]
    )

    resultados = []

    for producto in productos:
        resultados.append(
            {
                "id": producto.id,
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "marca": (
                    producto.marca
                    or ""
                ),
                "stock": producto.stock_actual,
                "precio_venta": str(
                    producto.precio_venta
                ),
            }
        )

    return JsonResponse(
        {
            "resultados": resultados,
        }
    )


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
            Q(codigo_venta__icontains=busqueda)
            | Q(cliente__nombre__icontains=busqueda)
            | Q(cliente__documento__icontains=busqueda)
            | Q(
                nombre_cliente_ocasional__icontains=busqueda
            )
            | Q(
                documento_cliente_ocasional__icontains=busqueda
            )
            | Q(
                telefono_cliente_ocasional__icontains=busqueda
            )
            | Q(numero_comprobante__icontains=busqueda)
            | Q(
                usuario_registro__username__icontains=busqueda
            )
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

        formulario_valido = formulario.is_valid()

        detalles_validos = (
            detalles_formset.is_valid()
        )

        pago_inicial_valido = False

        if formulario_valido and detalles_validos:
            pago_inicial_valido = (
                validar_pago_inicial_venta(
                    formulario,
                    detalles_formset,
                )
            )

        if (
            formulario_valido
            and detalles_validos
            and pago_inicial_valido
        ):
            with transaction.atomic():
                venta = formulario.save(
                    commit=False,
                )

                venta.usuario_registro = (
                    request.user
                )

                venta.estado = (
                    Venta.EstadoVenta.BORRADOR
                )

                venta.save()

                detalles_formset.instance = venta
                detalles_formset.save()

                venta.actualizar_total()

            messages.success(
                request,
                (
                    f"La venta N.º {venta.id} fue "
                    "registrada correctamente en "
                    "estado borrador."
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
        "datos_productos": obtener_datos_productos_venta(),
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
            "usuario_confirmacion",
            "usuario_anulacion",
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
def comprobante_venta_pdf(request, venta_id):
    """
    Genera el comprobante PDF individual de una venta
    confirmada o anulada.
    """

    venta = get_object_or_404(
        Venta.objects
        .select_related(
            "cliente",
            "usuario_registro",
            "usuario_confirmacion",
            "usuario_anulacion",
        )
        .prefetch_related(
            "detalles__producto",
        ),
        id=venta_id,
    )

    if venta.estado == Venta.EstadoVenta.BORRADOR:
        messages.error(
            request,
            (
                "No se puede generar el comprobante porque "
                "la venta todavía está en borrador."
            ),
        )

        return redirect(
            "ventas:detalle_venta",
            venta_id=venta.id,
        )

    if not venta.codigo_venta:
        messages.error(
            request,
            (
                "No se puede generar el comprobante porque "
                "la venta no tiene código interno."
            ),
        )

        return redirect(
            "ventas:detalle_venta",
            venta_id=venta.id,
        )

    detalles = list(
        venta.detalles.all()
    )

    if not detalles:
        messages.error(
            request,
            (
                "No se puede generar el comprobante porque "
                "la venta no contiene productos."
            ),
        )

        return redirect(
            "ventas:detalle_venta",
            venta_id=venta.id,
        )

    configuracion_reportes = (
        ConfiguracionReportes.objects.first()
    )

    ruta_logo = None

    if (
        configuracion_reportes
        and configuracion_reportes.logo
    ):
        try:
            ruta_logo = (
                configuracion_reportes.logo.path
            )
        except (ValueError, OSError):
            ruta_logo = None

    nombre_archivo = (
        f"{venta.codigo_venta}.pdf"
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
        bottomMargin=1.6 * cm,
        title=(
            f"Comprobante de venta "
            f"{venta.codigo_venta}"
        ),
        author="FABRI-CAR",
    )

    estilos_base = getSampleStyleSheet()

    estilo_empresa = ParagraphStyle(
        "EmpresaComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=19,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_subtitulo = ParagraphStyle(
        "SubtituloComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )

    estilo_codigo = ParagraphStyle(
        "CodigoComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#172b46"),
    )

    estilo_normal = ParagraphStyle(
        "NormalComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )

    estilo_etiqueta = ParagraphStyle(
        "EtiquetaComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    estilo_celda = ParagraphStyle(
        "CeldaComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
    )

    estilo_celda_centro = ParagraphStyle(
        "CeldaCentroComprobanteVenta",
        parent=estilo_celda,
        alignment=TA_CENTER,
    )

    estilo_celda_derecha = ParagraphStyle(
        "CeldaDerechaComprobanteVenta",
        parent=estilo_celda,
        alignment=TA_RIGHT,
    )

    estilo_cabecera_tabla = ParagraphStyle(
        "CabeceraTablaComprobanteVenta",
        parent=estilo_celda,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    estilo_cabecera_tabla_centro = ParagraphStyle(
        "CabeceraTablaCentroComprobanteVenta",
        parent=estilo_cabecera_tabla,
        alignment=TA_CENTER,
    )

    estilo_cabecera_tabla_derecha = ParagraphStyle(
        "CabeceraTablaDerechaComprobanteVenta",
        parent=estilo_cabecera_tabla,
        alignment=TA_RIGHT,
    )

    estilo_seccion = ParagraphStyle(
        "SeccionComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#172b46"),
        spaceAfter=5,
    )

    estilo_total = ParagraphStyle(
        "TotalComprobanteVenta",
        parent=estilos_base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#172b46"),
    )

    elementos = []

    # ---------------------------------------------------------
    # Encabezado
    # ---------------------------------------------------------

    logo_pdf = ""

    if ruta_logo:
        try:
            imagen_logo = ImageReader(
                ruta_logo
            )

            ancho_original, alto_original = (
                imagen_logo.getSize()
            )

            alto_logo = 1.6 * cm

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

    encabezado_empresa = [
        Paragraph(
            "COMPROBANTE DE VENTA",
            estilo_empresa,
        ),
        Paragraph(
            "Documento comercial interno",
            estilo_subtitulo,
        ),
    ]

    datos_codigo = [
        Paragraph(
            venta.codigo_venta,
            estilo_codigo,
        ),
        Paragraph(
            (
                "Fecha de venta: "
                f"{venta.fecha_venta.strftime('%d/%m/%Y')}"
            ),
            estilo_celda_derecha,
        ),
    ]

    tabla_encabezado = Table(
        [
            [
                logo_pdf,
                encabezado_empresa,
                datos_codigo,
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
            0.35 * cm,
        )
    )

    # ---------------------------------------------------------
    # Datos del cliente y de la venta
    # ---------------------------------------------------------

    telefono_cliente = ""

    if (
        venta.tipo_cliente
        == Venta.TipoCliente.OCASIONAL
    ):
        telefono_cliente = (
            venta.telefono_cliente_ocasional
        )

    elif venta.cliente:
        telefono_cliente = (
            getattr(
                venta.cliente,
                "telefono",
                "",
            )
            or getattr(
                venta.cliente,
                "celular",
                "",
            )
        )

    if venta.estado == Venta.EstadoVenta.ANULADA:
        estado_parrafo = Paragraph(
            (
                '<font color="#b91c1c">'
                "<b>ANULADA</b>"
                "</font>"
            ),
            estilo_normal,
        )

    else:
        estado_parrafo = Paragraph(
            (
                '<font color="#166534">'
                "<b>CONFIRMADA</b>"
                "</font>"
            ),
            estilo_normal,
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
                "Tipo de cliente",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.get_tipo_cliente_display()
                ),
                estilo_normal,
            ),
        ],
        [
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
            Paragraph(
                "Teléfono",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    telefono_cliente
                ),
                estilo_normal,
            ),
        ],
        [
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
            Paragraph(
                "Estado",
                estilo_etiqueta,
            ),
            estado_parrafo,
        ],
        [
            Paragraph(
                "Comprobante externo",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.get_tipo_comprobante_display()
                ),
                estilo_normal,
            ),
            Paragraph(
                "Número externo",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    venta.numero_comprobante
                ),
                estilo_normal,
            ),
        ],
    ]

    tabla_datos_generales = Table(
        datos_generales,
        colWidths=[
            3.2 * cm,
            5.8 * cm,
            3.2 * cm,
            5.8 * cm,
        ],
    )

    tabla_datos_generales.setStyle(
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
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elementos.append(
        tabla_datos_generales
    )

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    # ---------------------------------------------------------
    # Productos vendidos
    # ---------------------------------------------------------

    elementos.append(
        Paragraph(
            "Productos vendidos",
            estilo_seccion,
        )
    )

    datos_productos = [
        [
            Paragraph(
                "N.º",
                estilo_cabecera_tabla_centro,
            ),
            Paragraph(
                "Código",
                estilo_cabecera_tabla_centro,
            ),
            Paragraph(
                "Producto",
                estilo_cabecera_tabla,
            ),
            Paragraph(
                "Cant.",
                estilo_cabecera_tabla_centro,
            ),
            Paragraph(
                "Precio unit.",
                estilo_cabecera_tabla_derecha,
            ),
            Paragraph(
                "Subtotal",
                estilo_cabecera_tabla_derecha,
            ),
        ]
    ]

    for numero, detalle in enumerate(
        detalles,
        start=1,
    ):
        datos_productos.append(
            [
                Paragraph(
                    str(numero),
                    estilo_celda_centro,
                ),
                Paragraph(
                    texto_seguro_pdf(
                        detalle.producto.codigo
                    ),
                    estilo_celda_centro,
                ),
                Paragraph(
                    texto_seguro_pdf(
                        detalle.producto.nombre
                    ),
                    estilo_celda,
                ),
                Paragraph(
                    str(detalle.cantidad),
                    estilo_celda_centro,
                ),
                Paragraph(
                    f"Bs {detalle.precio_unitario:.2f}",
                    estilo_celda_derecha,
                ),
                Paragraph(
                    f"Bs {detalle.subtotal:.2f}",
                    estilo_celda_derecha,
                ),
            ]
        )

    tabla_productos = Table(
        datos_productos,
        colWidths=[
            0.8 * cm,
            2.5 * cm,
            6.7 * cm,
            1.7 * cm,
            3 * cm,
            3.3 * cm,
        ],
        repeatRows=1,
    )

    tabla_productos.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1f2937"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
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
        )
    )

    elementos.append(
        tabla_productos
    )

    elementos.append(
        Spacer(
            1,
            0.25 * cm,
        )
    )

    # ---------------------------------------------------------
    # Total
    # ---------------------------------------------------------

    tabla_total = Table(
        [
            [
                Paragraph(
                    "TOTAL GENERAL",
                    estilo_total,
                ),
                Paragraph(
                    f"Bs {venta.total:.2f}",
                    estilo_total,
                ),
            ]
        ],
        colWidths=[
            13.5 * cm,
            4.5 * cm,
        ],
    )

    tabla_total.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#e2e8f0"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, 0),
                    0.8,
                    colors.HexColor("#64748b"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
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
        tabla_total
    )

    # ---------------------------------------------------------
    # Observaciones
    # ---------------------------------------------------------

    if venta.observaciones:
        elementos.append(
            Spacer(
                1,
                0.4 * cm,
            )
        )

        elementos.append(
            Paragraph(
                "Observaciones",
                estilo_seccion,
            )
        )

        tabla_observaciones = Table(
            [
                [
                    Paragraph(
                        texto_seguro_pdf(
                            venta.observaciones
                        ),
                        estilo_normal,
                    )
                ]
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
    # Información de anulación
    # ---------------------------------------------------------

    if venta.estado == Venta.EstadoVenta.ANULADA:
        elementos.append(
            Spacer(
                1,
                0.4 * cm,
            )
        )

        elementos.append(
            Paragraph(
                "Información de anulación",
                estilo_seccion,
            )
        )

        tabla_anulacion = Table(
            [
                [
                    Paragraph(
                        "Anulada por",
                        estilo_etiqueta,
                    ),
                    Paragraph(
                        texto_seguro_pdf(
                            (
                                venta.usuario_anulacion
                                .get_username()
                                if venta.usuario_anulacion
                                else ""
                            )
                        ),
                        estilo_normal,
                    ),
                    Paragraph(
                        "Fecha",
                        estilo_etiqueta,
                    ),
                    Paragraph(
                        fecha_hora_pdf(
                            venta.fecha_anulacion
                        ),
                        estilo_normal,
                    ),
                ],
                [
                    Paragraph(
                        "Motivo",
                        estilo_etiqueta,
                    ),
                    Paragraph(
                        texto_seguro_pdf(
                            venta.motivo_anulacion
                        ),
                        estilo_normal,
                    ),
                    "",
                    "",
                ],
            ],
            colWidths=[
                3.2 * cm,
                5.8 * cm,
                3.2 * cm,
                5.8 * cm,
            ],
        )

        tabla_anulacion.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.HexColor("#fee2e2"),
                    ),
                    (
                        "BACKGROUND",
                        (2, 0),
                        (2, 0),
                        colors.HexColor("#fee2e2"),
                    ),
                    (
                        "SPAN",
                        (1, 1),
                        (3, 1),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#fca5a5"),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
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
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        elementos.append(
            tabla_anulacion
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

    elementos.append(
        Paragraph(
            "Auditoría de la operación",
            estilo_seccion,
        )
    )

    auditoria = [
        [
            Paragraph(
                "Registrada por",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    (
                        venta.usuario_registro
                        .get_username()
                        if venta.usuario_registro
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
                    venta.fecha_registro
                ),
                estilo_normal,
            ),
        ],
        [
            Paragraph(
                "Confirmada por",
                estilo_etiqueta,
            ),
            Paragraph(
                texto_seguro_pdf(
                    (
                        venta.usuario_confirmacion
                        .get_username()
                        if venta.usuario_confirmacion
                        else ""
                    )
                ),
                estilo_normal,
            ),
            Paragraph(
                "Fecha de confirmación",
                estilo_etiqueta,
            ),
            Paragraph(
                fecha_hora_pdf(
                    venta.fecha_confirmacion
                ),
                estilo_normal,
            ),
        ],
    ]

    tabla_auditoria = Table(
        auditoria,
        colWidths=[
            3.2 * cm,
            5.8 * cm,
            3.2 * cm,
            5.8 * cm,
        ],
    )

    tabla_auditoria.setStyle(
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
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    elementos.append(
        tabla_auditoria
    )

    # ---------------------------------------------------------
    # Marca de agua y pie de página
    # ---------------------------------------------------------

    def decorar_pagina(
        canvas,
        documento_pdf,
    ):
        if venta.estado == Venta.EstadoVenta.ANULADA:
            canvas.saveState()

            ancho_pagina, _ = A4

            ancho_sello = 7.2 * cm
            alto_sello = 1.05 * cm

            posicion_x = (
                ancho_pagina - ancho_sello
            ) / 2

            posicion_y = 1.45 * cm

            canvas.setStrokeColor(
                colors.HexColor("#dc2626")
            )

            canvas.setFillColor(
                colors.HexColor("#dc2626")
            )

            canvas.setLineWidth(
                1.4
            )

            canvas.roundRect(
                posicion_x,
                posicion_y,
                ancho_sello,
                alto_sello,
                0.12 * cm,
                stroke=1,
                fill=0,
            )

            canvas.setFont(
                "Helvetica-Bold",
                20,
            )

            canvas.drawCentredString(
                ancho_pagina / 2,
                posicion_y + 0.33 * cm,
                "VENTA ANULADA",
            )

            canvas.restoreState()

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
            0.85 * cm,
            ancho_pagina - 1.5 * cm,
            0.85 * cm,
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
            0.48 * cm,
            (
                "Comprobante generado automáticamente "
                "por FABRI-CAR"
            ),
        )

        canvas.drawRightString(
            ancho_pagina - 1.5 * cm,
            0.48 * cm,
            (
                f"Página "
                f"{documento_pdf.page}"
            ),
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

        formulario_valido = formulario.is_valid()

        detalles_validos = (
            detalles_formset.is_valid()
        )

        pago_inicial_valido = False

        if formulario_valido and detalles_validos:
            pago_inicial_valido = (
                validar_pago_inicial_venta(
                    formulario,
                    detalles_formset,
                )
            )

        if (
            formulario_valido
            and detalles_validos
            and pago_inicial_valido
        ):
            with transaction.atomic():
                venta = formulario.save(
                    commit=False,
                )

                venta.estado = (
                    Venta.EstadoVenta.BORRADOR
                )

                venta.save()

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
        "datos_productos": obtener_datos_productos_venta(),
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
    """
    Confirma una venta, asigna su código interno,
    descuenta el inventario y registra la auditoría.
    """

    with transaction.atomic():
        venta = get_object_or_404(
            Venta.objects.select_for_update(),
            id=venta_id,
        )

        if venta.estado != Venta.EstadoVenta.BORRADOR:
            messages.error(
                request,
                (
                    "Solo las ventas en estado borrador "
                    "pueden confirmarse."
                ),
            )

            return redirect(
                "ventas:detalle_venta",
                venta_id=venta.id,
            )

        if (
            venta.forma_pago
            == Venta.FormaPago.CREDITO
        ):
            if not venta.fecha_vencimiento_credito:
                messages.error(
                    request,
                    (
                        "La venta a crédito no tiene "
                        "fecha de vencimiento."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

            if (
                venta.fecha_vencimiento_credito
                < venta.fecha_venta
            ):
                messages.error(
                    request,
                    (
                        "La fecha de vencimiento no puede "
                        "ser anterior a la fecha de venta."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

            if (
                venta.monto_pago_inicial
                > venta.total
            ):
                messages.error(
                    request,
                    (
                        "El pago inicial no puede superar "
                        f"el total de la venta de "
                        f"Bs {venta.total:.2f}."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

            if (
                venta.monto_pago_inicial
                > Decimal("0.00")
                and not venta.metodo_pago_inicial
            ):
                messages.error(
                    request,
                    (
                        "Debe registrar el método "
                        "del pago inicial."
                    ),
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
                (
                    "La venta no puede confirmarse porque "
                    "no contiene productos."
                ),
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
                .filter(
                    id__in=productos_ids,
                )
                .order_by("id")
            )
        }

        # Primero validamos todos los productos.
        # No se modifica stock hasta completar esta revisión.
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
                        f'Stock insuficiente para '
                        f'"{producto.nombre}". '
                        f"Disponible: {producto.stock_actual}; "
                        f"solicitado: {detalle.cantidad}."
                    ),
                )

                return redirect(
                    "ventas:detalle_venta",
                    venta_id=venta.id,
                )

        # Después de validar todo, descontamos el stock.
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
                    f"Confirmación de la venta "
                    f"N.º {venta.id}"
                ),
                observaciones=(
                    "Comprobante externo: "
                    f"{venta.numero_comprobante or 'No registrado'}"
                ),
                usuario=request.user,
            )

        if not venta.codigo_venta:
            venta.codigo_venta = generar_codigo_venta(
                venta
            )

        venta.estado = Venta.EstadoVenta.CONFIRMADA
        venta.usuario_confirmacion = request.user
        venta.fecha_confirmacion = timezone.now()

        venta.save(
            update_fields=[
                "codigo_venta",
                "estado",
                "usuario_confirmacion",
                "fecha_confirmacion",
                "fecha_modificacion",
            ]
        )

        # La creación del crédito queda dentro de la misma
        # transacción que la confirmación y el descuento de stock.
        if (
            venta.forma_pago
            == Venta.FormaPago.CREDITO
        ):
            credito, credito_creado = (
                Credito.objects.get_or_create(
                    venta=venta,
                    defaults={
                        "fecha_inicio": (
                            venta.fecha_venta
                        ),
                        "fecha_vencimiento": (
                            venta
                            .fecha_vencimiento_credito
                        ),
                        "monto_total": venta.total,
                        "saldo_pendiente": venta.total,
                        "estado": (
                            Credito
                            .EstadoCredito
                            .PENDIENTE
                        ),
                        "observaciones": (
                            "Crédito generado por la "
                            f"venta {venta.codigo_venta}."
                        ),
                        "usuario_registro": (
                            request.user
                        ),
                    },
                )
            )

            if (
                credito_creado
                and venta.monto_pago_inicial
                > Decimal("0.00")
            ):
                PagoCredito.objects.create(
                    credito=credito,
                    fecha_pago=venta.fecha_venta,
                    monto=venta.monto_pago_inicial,
                    metodo_pago=(
                        venta.metodo_pago_inicial
                    ),
                    referencia=(
                        venta.referencia_pago_inicial
                    ),
                    observaciones=(
                        "Pago inicial registrado "
                        "automáticamente al confirmar "
                        f"la venta {venta.codigo_venta}."
                    ),
                    usuario_registro=request.user,
                )

    messages.success(
        request,
        (
            f"La venta {venta.codigo_venta} fue confirmada "
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
    """
    Anula una venta, registra la auditoría y repone
    el stock cuando la venta estaba confirmada.
    """

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
            "ventas:detalle_venta",
            venta_id=venta_id,
        )

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
            .filter(
                venta=venta,
            )
            .first()
        )

        if credito and credito.pagos.exists():
            messages.error(
                request,
                (
                    "La venta no puede anularse porque "
                    "su crédito ya tiene pagos registrados."
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
                    .filter(
                        id__in=productos_ids,
                    )
                    .order_by("id")
                )
            }

            # Primero comprobamos que todos los productos existan.
            # No se repone stock hasta completar esta validación.
            for detalle in detalles:
                producto = productos_bloqueados.get(
                    detalle.producto_id
                )

                if producto is None:
                    messages.error(
                        request,
                        (
                            "No fue posible reponer el stock "
                            f'del producto "{detalle.producto.nombre}".'
                        ),
                    )

                    return redirect(
                        "ventas:detalle_venta",
                        venta_id=venta.id,
                    )

            # Después de validar, se repone el stock.
            for detalle in detalles:
                producto = productos_bloqueados[
                    detalle.producto_id
                ]

                stock_anterior = producto.stock_actual

                stock_posterior = (
                    stock_anterior
                    + detalle.cantidad
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
                        f"Anulación de la venta "
                        f"{venta.codigo_venta or venta.id}"
                    ),
                    observaciones=(
                        "Reversión de salida por venta. "
                        "Motivo de anulación: "
                        f"{motivo_anulacion}"
                    ),
                    usuario=request.user,
                )

        venta.estado = Venta.EstadoVenta.ANULADA
        venta.usuario_anulacion = request.user
        venta.fecha_anulacion = timezone.now()
        venta.motivo_anulacion = motivo_anulacion

        venta.save(
            update_fields=[
                "estado",
                "usuario_anulacion",
                "fecha_anulacion",
                "motivo_anulacion",
                "fecha_modificacion",
            ]
        )

        if credito:
            credito.estado = (
                Credito.EstadoCredito.ANULADO
            )

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
                f"La venta "
                f"{venta.codigo_venta or venta.id} "
                "fue anulada y el stock fue repuesto "
                "correctamente."
            ),
        )

    else:
        messages.success(
            request,
            (
                f"La venta "
                f"{venta.codigo_venta or venta.id} "
                "fue anulada correctamente."
            ),
        )

    return redirect(
        "ventas:detalle_venta",
        venta_id=venta.id,
    )