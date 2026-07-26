from datetime import date
from decimal import Decimal
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q, Sum
from django.shortcuts import render
from django.http import HttpResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportes.pdf_utils import (
    crear_encabezado_y_pie,
    obtener_estilo_tabla,
    obtener_estilos_pdf,
)

from compras.models import Compra
from creditos.models import Credito
from principal.decorators import rol_requerido
from productos.models import Producto
from ventas.models import Venta


@login_required
@rol_requerido("Administrador", "Empleado")
def panel_reportes(request):
    """Muestra un resumen general de las operaciones del sistema."""

    ventas_confirmadas = Venta.objects.filter(
        estado=Venta.EstadoVenta.CONFIRMADA,
    )

    compras_confirmadas = Compra.objects.filter(
        estado=Compra.EstadoCompra.CONFIRMADA,
    )

    creditos_pendientes = Credito.objects.exclude(
        estado__in=[
            Credito.EstadoCredito.PAGADO,
            Credito.EstadoCredito.ANULADO,
        ]
    )

    productos_bajo_stock = Producto.objects.filter(
        estado=True,
        stock_actual__lte=F("stock_minimo"),
    )

    total_ventas = (
        ventas_confirmadas.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    total_compras = (
        compras_confirmadas.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    saldo_creditos = (
        creditos_pendientes.aggregate(
            total=Sum("saldo_pendiente")
        )["total"]
        or Decimal("0.00")
    )

    contexto = {
        "total_ventas": total_ventas,
        "total_compras": total_compras,
        "saldo_creditos": saldo_creditos,
        "cantidad_ventas": ventas_confirmadas.count(),
        "cantidad_compras": compras_confirmadas.count(),
        "cantidad_creditos": creditos_pendientes.count(),
        "cantidad_bajo_stock": productos_bajo_stock.count(),
    }

    return render(
        request,
        "reportes/panel_reportes.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_ventas(request):
    """Muestra el reporte detallado de ventas registradas."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    fecha_inicio_texto = request.GET.get(
        "fecha_inicio",
        "",
    ).strip()

    fecha_fin_texto = request.GET.get(
        "fecha_fin",
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
        )

    fecha_inicio = None
    fecha_fin = None

    try:
        if fecha_inicio_texto:
            fecha_inicio = date.fromisoformat(
                fecha_inicio_texto
            )
    except ValueError:
        fecha_inicio_texto = ""

    try:
        if fecha_fin_texto:
            fecha_fin = date.fromisoformat(
                fecha_fin_texto
            )
    except ValueError:
        fecha_fin_texto = ""

    if fecha_inicio:
        ventas = ventas.filter(
            fecha_venta__gte=fecha_inicio,
        )

    if fecha_fin:
        ventas = ventas.filter(
            fecha_venta__lte=fecha_fin,
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

    total_filtrado = (
        ventas.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_resultados = ventas.count()

    paginador = Paginator(
        ventas,
        15,
    )

    pagina_ventas = paginador.get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "ventas": pagina_ventas,
        "pagina_ventas": pagina_ventas,
        "busqueda": busqueda,
        "fecha_inicio": fecha_inicio_texto,
        "fecha_fin": fecha_fin_texto,
        "filtro_estado": filtro_estado,
        "filtro_pago": filtro_pago,
        "estados_venta": Venta.EstadoVenta.choices,
        "formas_pago": Venta.FormaPago.choices,
        "total_filtrado": total_filtrado,
        "cantidad_resultados": cantidad_resultados,
    }

    return render(
        request,
        "reportes/reporte_ventas.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_ventas_pdf(request):
    """Genera el reporte de ventas en formato PDF."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    fecha_inicio_texto = request.GET.get(
        "fecha_inicio",
        "",
    ).strip()

    fecha_fin_texto = request.GET.get(
        "fecha_fin",
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
        )

    fecha_inicio = None
    fecha_fin = None

    try:
        if fecha_inicio_texto:
            fecha_inicio = date.fromisoformat(
                fecha_inicio_texto
            )
    except ValueError:
        fecha_inicio_texto = ""

    try:
        if fecha_fin_texto:
            fecha_fin = date.fromisoformat(
                fecha_fin_texto
            )
    except ValueError:
        fecha_fin_texto = ""

    if fecha_inicio:
        ventas = ventas.filter(
            fecha_venta__gte=fecha_inicio,
        )

    if fecha_fin:
        ventas = ventas.filter(
            fecha_venta__lte=fecha_fin,
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

    total_filtrado = (
        ventas.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_resultados = ventas.count()

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'attachment; filename="reporte_ventas.pdf"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=(29.7 * cm, 21 * cm),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.4 * cm,
        bottomMargin=1.8 * cm,
        title="Reporte de ventas - FABRI-CAR",
        author="FABRI-CAR",
    )

    estilos = obtener_estilos_pdf()

    estilo_normal = estilos["normal"]
    estilo_filtros = estilos["filtros"]
    estilo_resumen = estilos["resumen"]

    elementos = []

    filtros_aplicados = []

    if busqueda:
        filtros_aplicados.append(
            f"Búsqueda: {busqueda}"
        )

    if fecha_inicio:
        filtros_aplicados.append(
            f"Desde: {fecha_inicio.strftime('%d/%m/%Y')}"
        )

    if fecha_fin:
        filtros_aplicados.append(
            f"Hasta: {fecha_fin.strftime('%d/%m/%Y')}"
        )

    if filtro_estado in Venta.EstadoVenta.values:
        nombre_estado = dict(
            Venta.EstadoVenta.choices
        ).get(
            filtro_estado,
            filtro_estado,
        )

        filtros_aplicados.append(
            f"Estado: {nombre_estado}"
        )

    if filtro_pago in Venta.FormaPago.values:
        nombre_pago = dict(
            Venta.FormaPago.choices
        ).get(
            filtro_pago,
            filtro_pago,
        )

        filtros_aplicados.append(
            f"Forma de pago: {nombre_pago}"
        )

    if filtros_aplicados:
        texto_filtros = " | ".join(
            filtros_aplicados
        )
    else:
        texto_filtros = "Sin filtros aplicados"

    elementos.append(
        Paragraph(
            f"<b>Filtros aplicados:</b> {texto_filtros}",
            estilo_filtros,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    datos_tabla = [
        [
            Paragraph(
                "<b>Comprobante</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Cliente</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Fecha</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Forma de pago</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Estado</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Total</b>",
                estilo_normal,
            ),
        ]
    ]

    for venta in ventas:
        cliente = (
            venta.cliente.nombre
            if venta.cliente
            else "Sin cliente"
        )

        datos_tabla.append(
            [
                Paragraph(
                    str(venta.numero_comprobante),
                    estilo_normal,
                ),
                Paragraph(
                    str(cliente),
                    estilo_normal,
                ),
                Paragraph(
                    venta.fecha_venta.strftime(
                        "%d/%m/%Y"
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    venta.get_forma_pago_display(),
                    estilo_normal,
                ),
                Paragraph(
                    venta.get_estado_display(),
                    estilo_normal,
                ),
                Paragraph(
                    f"Bs {venta.total:.2f}",
                    estilo_normal,
                ),
            ]
        )

    if cantidad_resultados == 0:
        datos_tabla.append(
            [
                Paragraph(
                    (
                        "No se encontraron ventas con "
                        "los filtros aplicados."
                    ),
                    estilo_normal,
                ),
                "",
                "",
                "",
                "",
                "",
            ]
        )

    tabla = Table(
        datos_tabla,
        colWidths=[
            4 * cm,
            6 * cm,
            3 * cm,
            4 * cm,
            3.5 * cm,
            3.5 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    estilo_tabla = obtener_estilo_tabla()

    estilo_tabla.add(
        "ALIGN",
        (-1, 1),
        (-1, -1),
        "RIGHT",
    )

    if cantidad_resultados == 0:
        estilo_tabla.add(
            "SPAN",
            (0, 1),
            (-1, 1),
        )

        estilo_tabla.add(
            "ALIGN",
            (0, 1),
            (-1, 1),
            "CENTER",
        )

    tabla.setStyle(
        estilo_tabla
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    elementos.append(
        Paragraph(
            (
                "<b>Total general de ventas:</b> "
                f"Bs {total_filtrado:.2f}"
            ),
            estilo_resumen,
        )
    )

    encabezado_y_pie = crear_encabezado_y_pie(
        request=request,
        titulo_reporte="Reporte de ventas",
        texto_cantidad=(
            f"Ventas encontradas: {cantidad_resultados}"
        ),
        texto_total=(
            f"Total: Bs {total_filtrado:.2f}"
        ),
    )

    documento.build(
        elementos,
        onFirstPage=encabezado_y_pie,
        onLaterPages=encabezado_y_pie,
    )

    return response

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_compras(request):
    """Muestra el reporte detallado de compras registradas."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    fecha_inicio_texto = request.GET.get(
        "fecha_inicio",
        "",
    ).strip()

    fecha_fin_texto = request.GET.get(
        "fecha_fin",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    compras = Compra.objects.select_related(
        "proveedor",
        "usuario_registro",
    )

    if busqueda:
        compras = compras.filter(
            Q(proveedor__nombre__icontains=busqueda)
            | Q(numero_comprobante__icontains=busqueda)
        )

    fecha_inicio = None
    fecha_fin = None

    try:
        if fecha_inicio_texto:
            fecha_inicio = date.fromisoformat(
                fecha_inicio_texto
            )
    except ValueError:
        fecha_inicio_texto = ""

    try:
        if fecha_fin_texto:
            fecha_fin = date.fromisoformat(
                fecha_fin_texto
            )
    except ValueError:
        fecha_fin_texto = ""

    if fecha_inicio:
        compras = compras.filter(
            fecha_compra__gte=fecha_inicio,
        )

    if fecha_fin:
        compras = compras.filter(
            fecha_compra__lte=fecha_fin,
        )

    if filtro_estado in Compra.EstadoCompra.values:
        compras = compras.filter(
            estado=filtro_estado,
        )

    compras = compras.order_by(
        "-fecha_compra",
        "-id",
    )

    total_filtrado = (
        compras.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_resultados = compras.count()

    paginador = Paginator(
        compras,
        15,
    )

    pagina_compras = paginador.get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "compras": pagina_compras,
        "pagina_compras": pagina_compras,
        "busqueda": busqueda,
        "fecha_inicio": fecha_inicio_texto,
        "fecha_fin": fecha_fin_texto,
        "filtro_estado": filtro_estado,
        "estados_compra": Compra.EstadoCompra.choices,
        "total_filtrado": total_filtrado,
        "cantidad_resultados": cantidad_resultados,
    }

    return render(
        request,
        "reportes/reporte_compras.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_compras_pdf(request):
    """Genera el reporte de compras en formato PDF."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    fecha_inicio_texto = request.GET.get(
        "fecha_inicio",
        "",
    ).strip()

    fecha_fin_texto = request.GET.get(
        "fecha_fin",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    compras = Compra.objects.select_related(
        "proveedor",
        "usuario_registro",
    )

    if busqueda:
        compras = compras.filter(
            Q(proveedor__nombre__icontains=busqueda)
            | Q(numero_comprobante__icontains=busqueda)
        )

    fecha_inicio = None
    fecha_fin = None

    try:
        if fecha_inicio_texto:
            fecha_inicio = date.fromisoformat(
                fecha_inicio_texto
            )
    except ValueError:
        fecha_inicio_texto = ""

    try:
        if fecha_fin_texto:
            fecha_fin = date.fromisoformat(
                fecha_fin_texto
            )
    except ValueError:
        fecha_fin_texto = ""

    if fecha_inicio:
        compras = compras.filter(
            fecha_compra__gte=fecha_inicio,
        )

    if fecha_fin:
        compras = compras.filter(
            fecha_compra__lte=fecha_fin,
        )

    if filtro_estado in Compra.EstadoCompra.values:
        compras = compras.filter(
            estado=filtro_estado,
        )

    compras = compras.order_by(
        "-fecha_compra",
        "-id",
    )

    total_filtrado = (
        compras.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_resultados = compras.count()

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'attachment; filename="reporte_compras.pdf"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=(29.7 * cm, 21 * cm),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.4 * cm,
        bottomMargin=1.8 * cm,
        title="Reporte de compras - FABRI-CAR",
        author="FABRI-CAR",
    )

    estilos = obtener_estilos_pdf()

    estilo_normal = estilos["normal"]
    estilo_filtros = estilos["filtros"]
    estilo_resumen = estilos["resumen"]

    elementos = []
    filtros_aplicados = []

    if busqueda:
        filtros_aplicados.append(
            f"Búsqueda: {busqueda}"
        )

    if fecha_inicio:
        filtros_aplicados.append(
            f"Desde: {fecha_inicio.strftime('%d/%m/%Y')}"
        )

    if fecha_fin:
        filtros_aplicados.append(
            f"Hasta: {fecha_fin.strftime('%d/%m/%Y')}"
        )

    if filtro_estado in Compra.EstadoCompra.values:
        nombre_estado = dict(
            Compra.EstadoCompra.choices
        ).get(
            filtro_estado,
            filtro_estado,
        )

        filtros_aplicados.append(
            f"Estado: {nombre_estado}"
        )

    if filtros_aplicados:
        texto_filtros = " | ".join(
            filtros_aplicados
        )
    else:
        texto_filtros = "Sin filtros aplicados"

    elementos.append(
        Paragraph(
            f"<b>Filtros aplicados:</b> {texto_filtros}",
            estilo_filtros,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    datos_tabla = [
        [
            Paragraph(
                "<b>Comprobante</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Proveedor</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Fecha</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Registrado por</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Estado</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Total</b>",
                estilo_normal,
            ),
        ]
    ]

    for compra in compras:
        proveedor = (
            str(compra.proveedor)
            if compra.proveedor
            else "Sin proveedor"
        )

        usuario_registro = (
            compra.usuario_registro.get_username()
            if compra.usuario_registro
            else "Sin usuario"
        )

        datos_tabla.append(
            [
                Paragraph(
                    str(compra.numero_comprobante),
                    estilo_normal,
                ),
                Paragraph(
                    str(proveedor),
                    estilo_normal,
                ),
                Paragraph(
                    compra.fecha_compra.strftime(
                        "%d/%m/%Y"
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    usuario_registro,
                    estilo_normal,
                ),
                Paragraph(
                    compra.get_estado_display(),
                    estilo_normal,
                ),
                Paragraph(
                    f"Bs {compra.total:.2f}",
                    estilo_normal,
                ),
            ]
        )

    if cantidad_resultados == 0:
        datos_tabla.append(
            [
                Paragraph(
                    (
                        "No se encontraron compras con "
                        "los filtros aplicados."
                    ),
                    estilo_normal,
                ),
                "",
                "",
                "",
                "",
                "",
            ]
        )

    tabla = Table(
        datos_tabla,
        colWidths=[
            4 * cm,
            6 * cm,
            3 * cm,
            4 * cm,
            3.5 * cm,
            3.5 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    estilo_tabla = obtener_estilo_tabla()

    estilo_tabla.add(
        "ALIGN",
        (-1, 1),
        (-1, -1),
        "RIGHT",
    )

    if cantidad_resultados == 0:
        estilo_tabla.add(
            "SPAN",
            (0, 1),
            (-1, 1),
        )

        estilo_tabla.add(
            "ALIGN",
            (0, 1),
            (-1, 1),
            "CENTER",
        )

    tabla.setStyle(
        estilo_tabla
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    elementos.append(
        Paragraph(
            (
                "<b>Total general de compras:</b> "
                f"Bs {total_filtrado:.2f}"
            ),
            estilo_resumen,
        )
    )

    encabezado_y_pie = crear_encabezado_y_pie(
        request=request,
        titulo_reporte="Reporte de compras",
        texto_cantidad=(
            f"Compras encontradas: {cantidad_resultados}"
        ),
        texto_total=(
            f"Total: Bs {total_filtrado:.2f}"
        ),
    )

    documento.build(
        elementos,
        onFirstPage=encabezado_y_pie,
        onLaterPages=encabezado_y_pie,
    )

    return response

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_bajo_stock(request):
    """Muestra productos agotados o con existencias mínimas."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_situacion = request.GET.get(
        "situacion",
        "",
    ).strip()

    productos = (
        Producto.objects
        .filter(
            estado=True,
            stock_actual__lte=F("stock_minimo"),
        )
        .annotate(
            unidades_faltantes=(
                F("stock_minimo") - F("stock_actual")
            )
        )
    )

    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(marca__icontains=busqueda)
        )

    if filtro_situacion == "AGOTADO":
        productos = productos.filter(
            stock_actual=0,
        )

    elif filtro_situacion == "BAJO":
        productos = productos.filter(
            stock_actual__gt=0,
            stock_actual__lte=F("stock_minimo"),
        )

    productos = productos.order_by(
        "stock_actual",
        "nombre",
    )

    cantidad_resultados = productos.count()

    cantidad_agotados = productos.filter(
        stock_actual=0,
    ).count()

    cantidad_bajo_stock = productos.filter(
        stock_actual__gt=0,
    ).count()

    paginador = Paginator(
        productos,
        15,
    )

    pagina_productos = paginador.get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "productos": pagina_productos,
        "pagina_productos": pagina_productos,
        "busqueda": busqueda,
        "filtro_situacion": filtro_situacion,
        "cantidad_resultados": cantidad_resultados,
        "cantidad_agotados": cantidad_agotados,
        "cantidad_bajo_stock": cantidad_bajo_stock,
    }

    return render(
        request,
        "reportes/reporte_bajo_stock.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_bajo_stock_pdf(request):
    """Genera el reporte de productos con bajo stock en PDF."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_situacion = request.GET.get(
        "situacion",
        "",
    ).strip()

    productos = (
        Producto.objects
        .filter(
            estado=True,
            stock_actual__lte=F("stock_minimo"),
        )
        .annotate(
            unidades_faltantes=(
                F("stock_minimo") - F("stock_actual")
            )
        )
    )

    if busqueda:
        productos = productos.filter(
            Q(codigo__icontains=busqueda)
            | Q(nombre__icontains=busqueda)
            | Q(marca__icontains=busqueda)
        )

    if filtro_situacion == "AGOTADO":
        productos = productos.filter(
            stock_actual=0,
        )

    elif filtro_situacion == "BAJO":
        productos = productos.filter(
            stock_actual__gt=0,
            stock_actual__lte=F("stock_minimo"),
        )

    productos = productos.order_by(
        "stock_actual",
        "nombre",
    )

    cantidad_resultados = productos.count()

    cantidad_agotados = productos.filter(
        stock_actual=0,
    ).count()

    cantidad_bajo_stock = productos.filter(
        stock_actual__gt=0,
    ).count()

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'attachment; filename="reporte_bajo_stock.pdf"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=(29.7 * cm, 21 * cm),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.4 * cm,
        bottomMargin=1.8 * cm,
        title="Reporte de bajo stock - FABRI-CAR",
        author="FABRI-CAR",
    )

    estilos = obtener_estilos_pdf()

    estilo_normal = estilos["normal"]
    estilo_filtros = estilos["filtros"]
    estilo_resumen = estilos["resumen"]

    elementos = []
    filtros_aplicados = []

    if busqueda:
        filtros_aplicados.append(
            f"Búsqueda: {busqueda}"
        )

    if filtro_situacion == "AGOTADO":
        filtros_aplicados.append(
            "Situación: Agotados"
        )

    elif filtro_situacion == "BAJO":
        filtros_aplicados.append(
            "Situación: Bajo stock"
        )

    if filtros_aplicados:
        texto_filtros = " | ".join(
            filtros_aplicados
        )
    else:
        texto_filtros = "Sin filtros aplicados"

    elementos.append(
        Paragraph(
            f"<b>Filtros aplicados:</b> {texto_filtros}",
            estilo_filtros,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    datos_tabla = [
        [
            Paragraph(
                "<b>Código</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Producto</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Marca</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Stock actual</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Stock mínimo</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Faltantes</b>",
                estilo_normal,
            ),
            Paragraph(
                "<b>Situación</b>",
                estilo_normal,
            ),
        ]
    ]

    for producto in productos:
        situacion = (
            "Agotado"
            if producto.stock_actual == 0
            else "Bajo stock"
        )

        marca = producto.marca or "Sin marca"

        datos_tabla.append(
            [
                Paragraph(
                    str(producto.codigo),
                    estilo_normal,
                ),
                Paragraph(
                    str(producto.nombre),
                    estilo_normal,
                ),
                Paragraph(
                    str(marca),
                    estilo_normal,
                ),
                Paragraph(
                    str(producto.stock_actual),
                    estilo_normal,
                ),
                Paragraph(
                    str(producto.stock_minimo),
                    estilo_normal,
                ),
                Paragraph(
                    str(producto.unidades_faltantes),
                    estilo_normal,
                ),
                Paragraph(
                    situacion,
                    estilo_normal,
                ),
            ]
        )

    if cantidad_resultados == 0:
        datos_tabla.append(
            [
                Paragraph(
                    (
                        "No se encontraron productos con "
                        "los filtros aplicados."
                    ),
                    estilo_normal,
                ),
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    tabla = Table(
        datos_tabla,
        colWidths=[
            3.2 * cm,
            6 * cm,
            3.5 * cm,
            3 * cm,
            3 * cm,
            3 * cm,
            3.5 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    estilo_tabla = obtener_estilo_tabla()

    estilo_tabla.add(
        "ALIGN",
        (3, 1),
        (5, -1),
        "CENTER",
    )

    if cantidad_resultados == 0:
        estilo_tabla.add(
            "SPAN",
            (0, 1),
            (-1, 1),
        )

        estilo_tabla.add(
            "ALIGN",
            (0, 1),
            (-1, 1),
            "CENTER",
        )

    tabla.setStyle(
        estilo_tabla
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    elementos.append(
        Paragraph(
            (
                f"<b>Productos encontrados:</b> "
                f"{cantidad_resultados} | "
                f"<b>Agotados:</b> {cantidad_agotados} | "
                f"<b>Bajo stock:</b> {cantidad_bajo_stock}"
            ),
            estilo_resumen,
        )
    )

    encabezado_y_pie = crear_encabezado_y_pie(
        request=request,
        titulo_reporte="Reporte de bajo stock",
        texto_cantidad=(
            f"Productos encontrados: {cantidad_resultados}"
        ),
        texto_total=(
            f"Agotados: {cantidad_agotados} | "
            f"Bajo stock: {cantidad_bajo_stock}"
        ),
    )

    documento.build(
        elementos,
        onFirstPage=encabezado_y_pie,
        onLaterPages=encabezado_y_pie,
    )

    return response

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_creditos(request):
    """Muestra el reporte de cuentas por cobrar."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    creditos = Credito.objects.select_related(
        "venta",
        "venta__cliente",
        "usuario_registro",
    )

    if busqueda:
        creditos = creditos.filter(
            Q(venta__cliente__nombre__icontains=busqueda)
            | Q(venta__cliente__documento__icontains=busqueda)
            | Q(venta__numero_comprobante__icontains=busqueda)
        )

    if filtro_estado == "VENCIDO":
        creditos = creditos.filter(
            fecha_vencimiento__lt=timezone.localdate(),
            saldo_pendiente__gt=Decimal("0.00"),
        ).exclude(
            estado__in=[
                Credito.EstadoCredito.PAGADO,
                Credito.EstadoCredito.ANULADO,
            ]
        )

    elif filtro_estado in Credito.EstadoCredito.values:
        creditos = creditos.filter(
            estado=filtro_estado,
        )

    creditos = creditos.order_by(
        "fecha_vencimiento",
        "-id",
    )

    total_saldo = (
        creditos.aggregate(
            total=Sum("saldo_pendiente")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_creditos = creditos.count()

    cantidad_vencidos = creditos.filter(
    fecha_vencimiento__lt=timezone.localdate(),
    saldo_pendiente__gt=Decimal("0.00"),
).exclude(
    estado__in=[
        Credito.EstadoCredito.PAGADO,
        Credito.EstadoCredito.ANULADO,
    ]
).count()

    paginador = Paginator(creditos, 15,)

    pagina_creditos = paginador.get_page(
        request.GET.get("pagina")
    )

    contexto = {
        "creditos": pagina_creditos,
        "pagina_creditos": pagina_creditos,
        "busqueda": busqueda,
        "filtro_estado": filtro_estado,
        "estados_credito": Credito.EstadoCredito.choices,
        "cantidad_creditos": cantidad_creditos,
        "cantidad_vencidos": cantidad_vencidos,
        "total_saldo": total_saldo,
    }

    return render(
        request,
        "reportes/reporte_creditos.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def reporte_creditos_pdf(request):
    """Genera el reporte de créditos en formato PDF."""

    busqueda = request.GET.get(
        "q",
        "",
    ).strip()

    filtro_estado = request.GET.get(
        "estado",
        "",
    ).strip()

    creditos = Credito.objects.select_related(
        "venta",
        "venta__cliente",
        "usuario_registro",
    )

    if busqueda:
        creditos = creditos.filter(
            Q(venta__cliente__nombre__icontains=busqueda)
            | Q(venta__cliente__documento__icontains=busqueda)
            | Q(venta__numero_comprobante__icontains=busqueda)
        )

    if filtro_estado == "VENCIDO":
        creditos = creditos.filter(
            fecha_vencimiento__lt=timezone.localdate(),
            saldo_pendiente__gt=Decimal("0.00"),
        ).exclude(
            estado__in=[
                Credito.EstadoCredito.PAGADO,
                Credito.EstadoCredito.ANULADO,
            ]
        )

    elif filtro_estado in Credito.EstadoCredito.values:
        creditos = creditos.filter(
            estado=filtro_estado,
        )

    creditos = creditos.order_by(
        "fecha_vencimiento",
        "-id",
    )

    total_saldo = (
        creditos.aggregate(
            total=Sum("saldo_pendiente")
        )["total"]
        or Decimal("0.00")
    )

    cantidad_creditos = creditos.count()

    cantidad_vencidos = creditos.filter(
        fecha_vencimiento__lt=timezone.localdate(),
        saldo_pendiente__gt=Decimal("0.00"),
    ).exclude(
        estado__in=[
            Credito.EstadoCredito.PAGADO,
            Credito.EstadoCredito.ANULADO,
        ]
    ).count()

    response = HttpResponse(
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        'attachment; filename="reporte_creditos.pdf"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=(29.7 * cm, 21 * cm),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.4 * cm,
        bottomMargin=1.8 * cm,
        title="Reporte de créditos - FABRI-CAR",
        author="FABRI-CAR",
    )

    estilos = obtener_estilos_pdf()

    estilo_normal = estilos["normal"]
    estilo_filtros = estilos["filtros"]
    estilo_resumen = estilos["resumen"]

    elementos = []
    filtros_aplicados = []

    if busqueda:
        filtros_aplicados.append(
            f"Búsqueda: {busqueda}"
        )

    if filtro_estado == "VENCIDO":
        filtros_aplicados.append(
            "Estado: Vencido"
        )

    elif filtro_estado in Credito.EstadoCredito.values:
        nombre_estado = dict(
            Credito.EstadoCredito.choices
        ).get(
            filtro_estado,
            filtro_estado,
        )

        filtros_aplicados.append(
            f"Estado: {nombre_estado}"
        )

    if filtros_aplicados:
        texto_filtros = " | ".join(
            filtros_aplicados
        )
    else:
        texto_filtros = "Sin filtros aplicados"

    elementos.append(
        Paragraph(
            f"<b>Filtros aplicados:</b> {texto_filtros}",
            estilo_filtros,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.4 * cm,
        )
    )

    datos_tabla = [
        [
            Paragraph("<b>Comprobante</b>", estilo_normal),
            Paragraph("<b>Cliente</b>", estilo_normal),
            Paragraph("<b>Vencimiento</b>", estilo_normal),
            Paragraph("<b>Estado</b>", estilo_normal),
            Paragraph("<b>Monto total</b>", estilo_normal),
            Paragraph("<b>Saldo pendiente</b>", estilo_normal),
        ]
    ]

    for credito in creditos:
        cliente = (
            str(credito.venta.cliente)
            if credito.venta and credito.venta.cliente
            else "Sin cliente"
        )

        comprobante = (
            credito.venta.numero_comprobante
            if credito.venta
            else "Sin comprobante"
        )

        monto_total = (
            credito.venta.total
            if credito.venta
            else Decimal("0.00")
        )

        datos_tabla.append(
            [
                Paragraph(
                    str(comprobante),
                    estilo_normal,
                ),
                Paragraph(
                    cliente,
                    estilo_normal,
                ),
                Paragraph(
                    credito.fecha_vencimiento.strftime(
                        "%d/%m/%Y"
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    credito.get_estado_display(),
                    estilo_normal,
                ),
                Paragraph(
                    f"Bs {monto_total:.2f}",
                    estilo_normal,
                ),
                Paragraph(
                    f"Bs {credito.saldo_pendiente:.2f}",
                    estilo_normal,
                ),
            ]
        )

    if cantidad_creditos == 0:
        datos_tabla.append(
            [
                Paragraph(
                    (
                        "No se encontraron créditos con "
                        "los filtros aplicados."
                    ),
                    estilo_normal,
                ),
                "",
                "",
                "",
                "",
                "",
            ]
        )

    tabla = Table(
        datos_tabla,
        colWidths=[
            4 * cm,
            6 * cm,
            3.5 * cm,
            3.5 * cm,
            4 * cm,
            4 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    estilo_tabla = obtener_estilo_tabla()

    estilo_tabla.add(
        "ALIGN",
        (-2, 1),
        (-1, -1),
        "RIGHT",
    )

    if cantidad_creditos == 0:
        estilo_tabla.add(
            "SPAN",
            (0, 1),
            (-1, 1),
        )

        estilo_tabla.add(
            "ALIGN",
            (0, 1),
            (-1, 1),
            "CENTER",
        )

    tabla.setStyle(
        estilo_tabla
    )

    elementos.append(tabla)

    elementos.append(
        Spacer(
            1,
            0.45 * cm,
        )
    )

    elementos.append(
        Paragraph(
            (
                "<b>Saldo pendiente total:</b> "
                f"Bs {total_saldo:.2f}"
            ),
            estilo_resumen,
        )
    )

    encabezado_y_pie = crear_encabezado_y_pie(
        request=request,
        titulo_reporte="Reporte de créditos",
        texto_cantidad=(
            f"Créditos encontrados: {cantidad_creditos}"
        ),
        texto_total=(
            f"Vencidos: {cantidad_vencidos} | "
            f"Saldo: Bs {total_saldo:.2f}"
        ),
    )

    documento.build(
        elementos,
        onFirstPage=encabezado_y_pie,
        onLaterPages=encabezado_y_pie,
    )

    return response