from xml.sax.saxutils import escape
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from productos.models import Producto
from principal.decorators import rol_requerido

from .forms import ParametroClasificacionForm
from .models import ParametroClasificacion, ResultadoClasificacion
from .services import ejecutar_clasificacion

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

UMBRAL_FAST_PREDETERMINADO = Decimal("0.60")
UMBRAL_SLOW_PREDETERMINADO = Decimal("0.25")


def obtener_periodo(tipo_periodo):
    """
    Devuelve la fecha inicial, la fecha final y el nombre
    correspondiente al período seleccionado.
    """

    hoy = timezone.localdate()

    if tipo_periodo == "mes":
        fecha_inicio = hoy.replace(
            day=1
        )

        nombre_periodo = "Este mes"

    elif tipo_periodo == "anio":
        fecha_inicio = hoy.replace(
            month=1,
            day=1,
        )

        nombre_periodo = "Este año"

    else:
        tipo_periodo = "semana"

        fecha_inicio = hoy - timedelta(
            days=hoy.weekday()
        )

        nombre_periodo = "Esta semana"

    return {
        "tipo": tipo_periodo,
        "nombre": nombre_periodo,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": hoy,
    }


def obtener_resultados(parametro):
    """
    Obtiene los productos clasificados y los ordena desde
    el más vendido hasta el menos vendido.
    """

    return (
        ResultadoClasificacion.objects
        .filter(parametro=parametro)
        .select_related("producto")
        .order_by(
            "-frecuencia",
            "producto__nombre",
        )
    )


def completar_resumen(resumen, resultados):
    """
    Agrega al resumen los indicadores comerciales
    que se mostrarán al usuario.
    """

    resultados_lista = list(
        resultados
    )

    total_unidades = sum(
        resultado.frecuencia
        for resultado in resultados_lista
    )

    producto_mas_vendido = (
        resultados_lista[0]
        if resultados_lista
        else None
    )

    productos_para_reponer = sum(
        1
        for resultado in resultados_lista
        if (
            resultado.producto.stock_actual
            <= resultado.producto.stock_minimo
        )
    )

    resumen_actualizado = {
        **resumen,
        "total_unidades": total_unidades,
        "productos_diferentes": len(
            resultados_lista
        ),
        "producto_mas_vendido": (
            producto_mas_vendido
        ),
        "productos_para_reponer": (
            productos_para_reponer
        ),
    }

    return (
        resumen_actualizado,
        resultados_lista,
    )


def obtener_o_crear_parametro_automatico(
    request,
    periodo,
):
    """
    Obtiene o crea el parámetro correspondiente al análisis
    automático de semana, mes o año.
    """

    nombre_analisis = (
        f"Análisis automático U{request.user.pk} - "
        f"{periodo['nombre']} - "
        f"{periodo['fecha_inicio']:%Y-%m-%d} "
        f"al {periodo['fecha_fin']:%Y-%m-%d}"
    )

    parametro = (
        ParametroClasificacion.objects
        .filter(
            nombre=nombre_analisis,
            fecha_inicio=periodo["fecha_inicio"],
            fecha_fin=periodo["fecha_fin"],
            usuario_registro=request.user,
        )
        .order_by("-id")
        .first()
    )

    if parametro is None:
        parametro = (
            ParametroClasificacion.objects.create(
                nombre=nombre_analisis,
                fecha_inicio=periodo["fecha_inicio"],
                fecha_fin=periodo["fecha_fin"],
                umbral_fast=(
                    UMBRAL_FAST_PREDETERMINADO
                ),
                umbral_slow=(
                    UMBRAL_SLOW_PREDETERMINADO
                ),
                usuario_registro=request.user,
            )
        )

    return parametro


@login_required
@rol_requerido("Administrador", "Empleado")
def clasificacion_automatica(request):
    """
    Muestra automáticamente la clasificación de la semana,
    el mes o el año actual.

    También permite ejecutar un análisis personalizado.
    """

    resultados = []
    resumen = None
    parametro = None

    tipo_periodo = request.GET.get(
        "periodo",
        "semana",
    ).strip().lower()

    periodo = obtener_periodo(
        tipo_periodo
    )

    fecha_inicio_analisis = (
        periodo["fecha_inicio"]
    )

    fecha_fin_analisis = (
        periodo["fecha_fin"]
    )

    periodo_seleccionado = (
        periodo["tipo"]
    )

    nombre_periodo = (
        periodo["nombre"]
    )

    if request.method == "POST":

        form = ParametroClasificacionForm(
            request.POST
        )

        if form.is_valid():

            parametro = form.save(
                commit=False
            )

            parametro.usuario_registro = (
                request.user
            )

            parametro.save()

            resumen_servicio = (
                ejecutar_clasificacion(
                    parametro
                )
            )

            consulta_resultados = (
                obtener_resultados(
                    parametro
                )
            )

            resumen, resultados = (
                completar_resumen(
                    resumen_servicio,
                    consulta_resultados,
                )
            )

            fecha_inicio_analisis = (
                parametro.fecha_inicio
            )

            fecha_fin_analisis = (
                parametro.fecha_fin
            )

            periodo_seleccionado = (
                "personalizado"
            )

            nombre_periodo = (
                "Período personalizado"
            )

            messages.success(
                request,
                (
                    "El análisis de ventas se "
                    "realizó correctamente."
                ),
            )

    else:

        form = ParametroClasificacionForm(
            initial={
                "nombre": (
                    f"Análisis personalizado "
                    f"{periodo['fecha_inicio']:%d/%m/%Y} "
                    f"al "
                    f"{periodo['fecha_fin']:%d/%m/%Y}"
                ),
                "fecha_inicio": (
                    periodo["fecha_inicio"]
                ),
                "fecha_fin": (
                    periodo["fecha_fin"]
                ),
                "umbral_fast": (
                    UMBRAL_FAST_PREDETERMINADO
                ),
                "umbral_slow": (
                    UMBRAL_SLOW_PREDETERMINADO
                ),
            }
        )

        parametro = (
            obtener_o_crear_parametro_automatico(
                request,
                periodo,
            )
        )

        resumen_servicio = (
            ejecutar_clasificacion(
                parametro
            )
        )

        consulta_resultados = (
            obtener_resultados(
                parametro
            )
        )

        resumen, resultados = (
            completar_resumen(
                resumen_servicio,
                consulta_resultados,
            )
        )

    # Filtros para consultar los resultados clasificados
    busqueda = request.GET.get(
        "busqueda",
        "",
    ).strip()

    marca = request.GET.get(
        "marca",
        "",
    ).strip()

    tipo = request.GET.get(
        "tipo",
        "",
    ).strip()

    condicion = request.GET.get(
        "condicion",
        "",
    ).strip()

    categoria = request.GET.get(
        "categoria",
        "",
    ).strip().upper()

    orden = request.GET.get(
        "orden",
        "mas_vendidos",
    ).strip()

    reposicion = request.GET.get(
        "reposicion",
        "",
    ).strip()

    if busqueda:
        resultados = [
            resultado
            for resultado in resultados
            if (
                busqueda.lower()
                in resultado.producto.nombre.lower()
                or busqueda.lower()
                in resultado.producto.codigo.lower()
            )
        ]

    if marca:
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.producto.marca
                and resultado.producto.marca.lower()
                == marca.lower()
            )
        ]

    if tipo:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.producto.tipo == tipo
        ]

    if condicion:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.producto.condicion == condicion
        ]

    if categoria:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.categoria == categoria
        ]

    if reposicion == "urgente":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "FAST"
                and resultado.producto.stock_actual
                <= resultado.producto.stock_minimo
            )
        ]

    elif reposicion == "pronto":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "SLOW"
                and resultado.producto.stock_actual
                <= resultado.producto.stock_minimo
            )
        ]

    elif reposicion == "suficiente":
        resultados = [
            resultado
            for resultado in resultados
            if resultado.producto.stock_actual
            > resultado.producto.stock_minimo
        ]

    elif reposicion == "no_comprar":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "NON"
                and resultado.producto.stock_actual > 0
            )
        ]

    if orden == "menos_vendidos":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.frecuencia,
                resultado.producto.nombre.lower(),
            ),
        )

    elif orden == "mayor_stock":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.stock_actual,
                resultado.producto.nombre.lower(),
            ),
            reverse=True,
        )

    elif orden == "menor_stock":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.stock_actual,
                resultado.producto.nombre.lower(),
            ),
        )

    elif orden == "nombre":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.nombre.lower()
            ),
        )

    elif orden == "marca":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                (
                    resultado.producto.marca
                    or ""
                ).lower(),
                resultado.producto.nombre.lower(),
            ),
        )

    else:
        orden = "mas_vendidos"

        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.frecuencia,
                resultado.producto.nombre.lower(),
            ),
            reverse=True,
        )

    tipos_disponibles = (
        Producto._meta
        .get_field("tipo")
        .choices
    )

    condiciones_disponibles = (
        Producto._meta
        .get_field("condicion")
        .choices
    )

    marcas_disponibles = (
        Producto.objects
        .exclude(marca__isnull=True)
        .exclude(marca="")
        .values_list("marca", flat=True)
        .distinct()
        .order_by("marca")
    )

    contexto = {
        "form": form,
        "resultados": resultados,
        "resumen": resumen,
        "fecha_inicio_analisis": fecha_inicio_analisis,
        "fecha_fin_analisis": fecha_fin_analisis,
        "periodo_seleccionado": periodo_seleccionado,
        "nombre_periodo": nombre_periodo,
        "busqueda": busqueda,
        "marca_seleccionada": marca,
        "tipo_seleccionado": tipo,
        "condicion_seleccionada": condicion,
        "categoria_seleccionada": categoria,
        "orden_seleccionado": orden,
        "reposicion_seleccionada": reposicion,
        "marcas_disponibles": marcas_disponibles,
        "tipos_disponibles": tipos_disponibles,
        "condiciones_disponibles": condiciones_disponibles,
        "parametro_id": parametro.id if parametro else None,
        "consulta_pdf": request.GET.urlencode(),
    }

    return render(
        request,
        "clasificacion/clasificacion.html",
        contexto,
    )

@login_required
@rol_requerido("Administrador", "Empleado")
def clasificacion_pdf(request, parametro_id):
    """
    Exporta a PDF el análisis de clasificación seleccionado.
    """

    parametro = get_object_or_404(
        ParametroClasificacion,
        id=parametro_id,
        usuario_registro=request.user,
    )

    resultados = list(
        obtener_resultados(parametro)
    )

    busqueda = request.GET.get(
        "busqueda",
        "",
    ).strip()

    marca = request.GET.get(
        "marca",
        "",
    ).strip()

    tipo = request.GET.get(
        "tipo",
        "",
    ).strip()

    condicion = request.GET.get(
        "condicion",
        "",
    ).strip()

    categoria = request.GET.get(
        "categoria",
        "",
    ).strip().upper()

    orden = request.GET.get(
        "orden",
        "mas_vendidos",
    ).strip()

    reposicion = request.GET.get(
        "reposicion",
        "",
    ).strip()

    # Aplicar filtros
    if busqueda:
        texto_busqueda = busqueda.lower()

        resultados = [
            resultado
            for resultado in resultados
            if (
                texto_busqueda
                in resultado.producto.nombre.lower()
                or texto_busqueda
                in resultado.producto.codigo.lower()
            )
        ]

    if marca:
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.producto.marca
                and resultado.producto.marca.lower()
                == marca.lower()
            )
        ]

    if tipo:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.producto.tipo == tipo
        ]

    if condicion:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.producto.condicion == condicion
        ]

    if categoria:
        resultados = [
            resultado
            for resultado in resultados
            if resultado.categoria == categoria
        ]

    if reposicion == "urgente":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "FAST"
                and resultado.producto.stock_actual
                <= resultado.producto.stock_minimo
            )
        ]

    elif reposicion == "pronto":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "SLOW"
                and resultado.producto.stock_actual
                <= resultado.producto.stock_minimo
            )
        ]

    elif reposicion == "suficiente":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.producto.stock_actual
                > resultado.producto.stock_minimo
            )
        ]

    elif reposicion == "no_comprar":
        resultados = [
            resultado
            for resultado in resultados
            if (
                resultado.categoria == "NON"
                and resultado.producto.stock_actual > 0
            )
        ]

    # Aplicar ordenamiento
    if orden == "menos_vendidos":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.frecuencia,
                resultado.producto.nombre.lower(),
            ),
        )

    elif orden == "mayor_stock":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.stock_actual,
                resultado.producto.nombre.lower(),
            ),
            reverse=True,
        )

    elif orden == "menor_stock":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.stock_actual,
                resultado.producto.nombre.lower(),
            ),
        )

    elif orden == "nombre":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.producto.nombre.lower()
            ),
        )

    elif orden == "marca":
        resultados = sorted(
            resultados,
            key=lambda resultado: (
                (
                    resultado.producto.marca
                    or ""
                ).lower(),
                resultado.producto.nombre.lower(),
            ),
        )

    else:
        orden = "mas_vendidos"

        resultados = sorted(
            resultados,
            key=lambda resultado: (
                resultado.frecuencia,
                resultado.producto.nombre.lower(),
            ),
            reverse=True,
        )

    total_unidades = sum(
        resultado.frecuencia
        for resultado in resultados
    )

    productos_para_reponer = sum(
        1
        for resultado in resultados
        if (
            resultado.producto.stock_actual
            <= resultado.producto.stock_minimo
        )
    )

    response = HttpResponse(
        content_type="application/pdf",
    )

    nombre_archivo = (
        "clasificacion_repuestos_"
        f"{parametro.fecha_inicio:%Y%m%d}_"
        f"{parametro.fecha_fin:%Y%m%d}.pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{nombre_archivo}"'
    )

    documento = SimpleDocTemplate(
        response,
        pagesize=(29.7 * cm, 21 * cm),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=3.4 * cm,
        bottomMargin=1.8 * cm,
        title="Clasificación automática de repuestos",
        author="FABRI-CAR",
    )

    estilos = obtener_estilos_pdf()

    estilo_normal = estilos["normal"]
    estilo_encabezado = estilos["encabezado"]
    estilo_filtros = estilos["filtros"]
    estilo_resumen = estilos["resumen"]

    elementos = []

    periodo_texto = (
        f"{parametro.fecha_inicio:%d/%m/%Y} "
        f"al {parametro.fecha_fin:%d/%m/%Y}"
    )

    elementos.append(
        Paragraph(
            (
                "<b>Período analizado:</b> "
                f"{periodo_texto}"
            ),
            estilo_filtros,
        )
    )

    filtros_aplicados = []

    if busqueda:
        filtros_aplicados.append(
            f"Búsqueda: {escape(busqueda)}"
        )

    if marca:
        filtros_aplicados.append(
            f"Marca: {escape(marca)}"
        )

    tipos = dict(
        Producto._meta.get_field("tipo").choices
    )

    condiciones = dict(
        Producto._meta.get_field(
            "condicion"
        ).choices
    )

    if tipo:
        filtros_aplicados.append(
            f"Tipo: {escape(str(tipos.get(tipo, tipo)))}"
        )

    if condicion:
        filtros_aplicados.append(
            (
                "Condición: "
                f"{escape(str(condiciones.get(condicion, condicion)))}"
            )
        )

    nombres_categoria = {
        "FAST": "Muy vendido",
        "SLOW": "Venta moderada",
        "NON": "Poco vendido",
    }

    if categoria:
        filtros_aplicados.append(
            (
                "Nivel de salida: "
                f"{nombres_categoria.get(categoria, categoria)}"
            )
        )

    nombres_reposicion = {
        "urgente": "Comprar urgentemente",
        "pronto": "Reponer pronto",
        "suficiente": "Stock suficiente",
        "no_comprar": "No comprar por ahora",
    }

    if reposicion:
        filtros_aplicados.append(
            (
                "Estado de reposición: "
                f"{nombres_reposicion.get(reposicion, reposicion)}"
            )
        )

    if filtros_aplicados:
        texto_filtros = " | ".join(
            filtros_aplicados
        )
    else:
        texto_filtros = "Sin filtros adicionales"

    elementos.append(
        Paragraph(
            (
                "<b>Filtros aplicados:</b> "
                f"{texto_filtros}"
            ),
            estilo_filtros,
        )
    )

    elementos.append(
        Spacer(
            1,
            0.35 * cm,
        )
    )

    elementos.append(
        Paragraph(
            (
                f"<b>Repuestos analizados:</b> "
                f"{len(resultados)}"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Unidades vendidas:</b> "
                f"{total_unidades}"
                f" &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Productos para revisar:</b> "
                f"{productos_para_reponer}"
            ),
            estilo_resumen,
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
            "N.º",
            "Código",
            "Repuesto",
            "Marca",
            "Tipo",
            "Condición",
            "Vendidos",
            "Stock",
            "Nivel",
            "Recomendación",
        ]
    ]

    for posicion, resultado in enumerate(
        resultados,
        start=1,
    ):
        producto = resultado.producto

        nivel_salida = (
            resultado.obtener_nivel_salida()
        )

        recomendacion = (
            resultado.obtener_recomendacion()
        )
        datos_tabla.append(
            [
                Paragraph(
                    str(posicion),
                    estilo_normal,
                ),
                Paragraph(
                    escape(str(producto.codigo)),
                    estilo_normal,
                ),
                Paragraph(
                    escape(str(producto.nombre)),
                    estilo_normal,
                ),
                Paragraph(
                    escape(
                        str(
                            producto.marca
                            or "Sin marca"
                        )
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    escape(
                        producto.get_tipo_display()
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    escape(
                        producto.get_condicion_display()
                    ),
                    estilo_normal,
                ),
                Paragraph(
                    str(resultado.frecuencia),
                    estilo_normal,
                ),
                Paragraph(
                    str(producto.stock_actual),
                    estilo_normal,
                ),
                Paragraph(
                    nivel_salida,
                    estilo_normal,
                ),
                Paragraph(
                    recomendacion,
                    estilo_normal,
                ),
            ]
        )

    if not resultados:
        datos_tabla.append(
            [
                Paragraph(
                    (
                        "No existen resultados con "
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
                "",
                "",
                "",
            ]
        )

    tabla = Table(
        datos_tabla,
        colWidths=[
            0.9 * cm,
            2.2 * cm,
            4.3 * cm,
            2.5 * cm,
            2.2 * cm,
            2.0 * cm,
            1.5 * cm,
            1.5 * cm,
            2.6 * cm,
            6.8 * cm,
        ],
        repeatRows=1,
        hAlign="CENTER",
    )

    tabla.setStyle(
        obtener_estilo_tabla()
    )

    if not resultados:
        tabla.setStyle(
            TableStyle(
                [
                    (
                        "SPAN",
                        (0, 1),
                        (-1, 1),
                    ),
                    (
                        "ALIGN",
                        (0, 1),
                        (-1, 1),
                        "CENTER",
                    ),
                ]
            )
        )

    elementos.append(tabla)

    encabezado_y_pie = crear_encabezado_y_pie(
        request,
        "Clasificación automática de repuestos",
        f"Productos: {len(resultados)}",
        f"Unidades: {total_unidades}",
    )

    documento.build(
        elementos,
        onFirstPage=encabezado_y_pie,
        onLaterPages=encabezado_y_pie,
    )

    return response