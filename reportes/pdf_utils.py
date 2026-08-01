from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import TableStyle

from reportes.models import ConfiguracionReportes


COLOR_PRINCIPAL = colors.HexColor("#1f2937")
COLOR_SECUNDARIO = colors.HexColor("#374151")
COLOR_TEXTO = colors.HexColor("#4b5563")
COLOR_BORDE = colors.HexColor("#9ca3af")
COLOR_BORDE_SUAVE = colors.HexColor("#d1d5db")
COLOR_FILA_ALTERNA = colors.HexColor("#f3f4f6")


def obtener_ruta_logo():
    """Obtiene la ruta del logo configurado para los reportes."""

    configuracion = ConfiguracionReportes.objects.first()

    if not configuracion or not configuracion.logo:
        return None

    try:
        return configuracion.logo.path
    except (ValueError, OSError):
        return None


def obtener_estilos_pdf():
    """Devuelve los estilos de texto comunes de los reportes."""

    estilo_normal = ParagraphStyle(
        name="ReporteNormal",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_PRINCIPAL,
    )

    estilo_encabezado = ParagraphStyle(
        name="ReporteEncabezadoTabla",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    estilo_filtros = ParagraphStyle(
        name="ReporteFiltros",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=COLOR_SECUNDARIO,
    )

    estilo_resumen = ParagraphStyle(
        name="ReporteResumen",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=COLOR_PRINCIPAL,
    )

    return {
        "normal": estilo_normal,
        "encabezado": estilo_encabezado,
        "filtros": estilo_filtros,
        "resumen": estilo_resumen,
    }


def obtener_estilo_tabla():
    """Devuelve el formato estándar para las tablas."""

    return TableStyle(
        [
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                COLOR_PRINCIPAL,
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
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                COLOR_BORDE,
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    COLOR_FILA_ALTERNA,
                ],
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6,
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


def crear_encabezado_y_pie(
    request,
    titulo_reporte,
    texto_cantidad,
    texto_total="",
):
    """
    Crea la función que dibuja el encabezado y pie
    de todas las páginas del PDF.
    """

    ruta_logo = obtener_ruta_logo()
    fecha_emision = timezone.localtime()
    usuario = request.user.get_username()

    def dibujar_encabezado_y_pie(
        canvas,
        documento_pdf,
    ):
        canvas.saveState()

        ancho_pagina, alto_pagina = (
            documento_pdf.pagesize
        )

        margen_izquierdo = 1.5 * cm
        margen_derecho = (
            ancho_pagina - 1.5 * cm
        )

        posicion_superior = (
            alto_pagina - 0.65 * cm
        )

        posicion_linea = (
            alto_pagina - 2.85 * cm
        )

        posicion_texto = margen_izquierdo

        if ruta_logo:
            try:
                imagen_logo = ImageReader(
                    ruta_logo
                )

                ancho_original, alto_original = (
                    imagen_logo.getSize()
                )

                alto_logo = 1.65 * cm

                ancho_logo = (
                    alto_logo
                    * ancho_original
                    / alto_original
                )

                ancho_maximo = 4.2 * cm

                if ancho_logo > ancho_maximo:
                    ancho_logo = ancho_maximo

                    alto_logo = (
                        ancho_logo
                        * alto_original
                        / ancho_original
                    )

                posicion_logo_y = (
                    alto_pagina
                    - 0.55 * cm
                    - alto_logo
                )

                canvas.drawImage(
                    imagen_logo,
                    margen_izquierdo,
                    posicion_logo_y,
                    width=ancho_logo,
                    height=alto_logo,
                    preserveAspectRatio=True,
                    mask="auto",
                )

                posicion_texto = (
                    margen_izquierdo
                    + ancho_logo
                    + 0.5 * cm
                )

            except (
                OSError,
                ValueError,
                TypeError,
            ):
                posicion_texto = margen_izquierdo

        canvas.setFillColor(
            COLOR_PRINCIPAL
        )

        canvas.setFont(
            "Helvetica-Bold",
            15,
        )

        canvas.drawString(
            posicion_texto,
            posicion_superior,
            "FABRI-CAR",
        )

        canvas.setFont(
            "Helvetica-Bold",
            11,
        )

        canvas.setFillColor(
            COLOR_SECUNDARIO
        )

        canvas.drawString(
            posicion_texto,
            posicion_superior - 0.55 * cm,
            titulo_reporte,
        )

        canvas.setFont(
            "Helvetica",
            8,
        )

        canvas.setFillColor(
            COLOR_TEXTO
        )

        canvas.drawString(
            posicion_texto,
            posicion_superior - 1.05 * cm,
            (
                "Fecha de emisión: "
                f"{fecha_emision.strftime('%d/%m/%Y %H:%M')}"
            ),
        )

        canvas.drawString(
            posicion_texto,
            posicion_superior - 1.45 * cm,
            f"Generado por: {usuario}",
        )

        canvas.setFont(
            "Helvetica-Bold",
            8,
        )

        canvas.setFillColor(
            COLOR_PRINCIPAL
        )

        canvas.drawRightString(
            margen_derecho,
            posicion_superior,
            texto_cantidad,
        )

        if texto_total:
            canvas.drawRightString(
                margen_derecho,
                posicion_superior - 0.5 * cm,
                texto_total,
            )

        canvas.setStrokeColor(
            COLOR_BORDE
        )

        canvas.setLineWidth(0.8)

        canvas.line(
            margen_izquierdo,
            posicion_linea,
            margen_derecho,
            posicion_linea,
        )

        canvas.setStrokeColor(
            COLOR_BORDE_SUAVE
        )

        canvas.setLineWidth(0.5)

        canvas.line(
            margen_izquierdo,
            1.1 * cm,
            margen_derecho,
            1.1 * cm,
        )

        canvas.setFont(
            "Helvetica",
            8,
        )

        canvas.setFillColor(
            COLOR_TEXTO
        )

        canvas.drawString(
            margen_izquierdo,
            0.7 * cm,
            "Sistema de gestión FABRI-CAR",
        )

        canvas.drawCentredString(
            ancho_pagina / 2,
            0.7 * cm,
            "Documento generado automáticamente",
        )

        canvas.drawRightString(
            margen_derecho,
            0.7 * cm,
            f"Página {documento_pdf.page}",
        )

        canvas.restoreState()

    return dibujar_encabezado_y_pie