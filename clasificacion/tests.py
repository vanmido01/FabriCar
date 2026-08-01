from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from productos.models import Producto
from ventas.models import DetalleVenta, Venta

from .forms import ParametroClasificacionForm
from .models import (
    ParametroClasificacion,
    ResultadoClasificacion,
)
from .services import ejecutar_clasificacion


class EjecutarClasificacionTest(TestCase):
    """Pruebas del cálculo automático de clasificación."""

    def setUp(self):
        usuario_modelo = get_user_model()

        self.usuario = usuario_modelo.objects.create_user(
            username="usuario_prueba",
            password="clave-segura-123",
        )

        self.cliente = Cliente.objects.create(
            nombre="Cliente de prueba",
            documento="PRUEBA-001",
        )

        self.producto_fast = Producto.objects.create(
            codigo="TEST-FAST",
            nombre="Producto de alta rotación",
            tipo=Producto.TipoRepuesto.ORIGINAL,
            condicion=Producto.CondicionProducto.NUEVO,
            marca="Marca A",
            precio_compra=Decimal("50.00"),
            precio_venta=Decimal("80.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.producto_slow = Producto.objects.create(
            codigo="TEST-SLOW",
            nombre="Producto de rotación moderada",
            tipo=Producto.TipoRepuesto.ALTERNATIVO,
            condicion=Producto.CondicionProducto.NUEVO,
            marca="Marca B",
            precio_compra=Decimal("40.00"),
            precio_venta=Decimal("65.00"),
            stock_actual=15,
            stock_minimo=5,
        )

        self.producto_non = Producto.objects.create(
            codigo="TEST-NON",
            nombre="Producto de baja rotación",
            tipo=Producto.TipoRepuesto.ESTANDAR,
            condicion=Producto.CondicionProducto.USADO,
            marca="Marca C",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=10,
            stock_minimo=3,
        )

        self.parametro = ParametroClasificacion.objects.create(
            nombre="Prueba de clasificación",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            umbral_fast=Decimal("0.60"),
            umbral_slow=Decimal("0.25"),
            usuario_registro=self.usuario,
        )

        self.venta_confirmada = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=date(2026, 7, 15),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-PRUEBA-001",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=self.venta_confirmada,
            producto=self.producto_fast,
            cantidad=6,
            precio_unitario=Decimal("80.00"),
        )

        DetalleVenta.objects.create(
            venta=self.venta_confirmada,
            producto=self.producto_slow,
            cantidad=3,
            precio_unitario=Decimal("65.00"),
        )

        DetalleVenta.objects.create(
            venta=self.venta_confirmada,
            producto=self.producto_non,
            cantidad=1,
            precio_unitario=Decimal("35.00"),
        )

        # Esta venta no debe considerarse porque está en borrador.
        venta_borrador = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=date(2026, 7, 16),
            estado=Venta.EstadoVenta.BORRADOR,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-BORRADOR",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta_borrador,
            producto=self.producto_fast,
            cantidad=50,
            precio_unitario=Decimal("80.00"),
        )

        # Esta venta no debe considerarse porque está fuera del período.
        venta_fuera_periodo = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=date(2026, 8, 1),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-FUERA-PERIODO",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta_fuera_periodo,
            producto=self.producto_fast,
            cantidad=50,
            precio_unitario=Decimal("80.00"),
        )

    def test_calcula_frecuencia_probabilidad_y_categoria(self):
        resumen = ejecutar_clasificacion(
            self.parametro
        )

        self.assertEqual(
            resumen,
            {
                "productos": 3,
                "fast": 1,
                "slow": 1,
                "non": 1,
            },
        )

        resultados = (
            ResultadoClasificacion.objects
            .filter(parametro=self.parametro)
        )

        self.assertEqual(
            resultados.count(),
            3,
        )

        resultado_fast = resultados.get(
            producto=self.producto_fast
        )

        resultado_slow = resultados.get(
            producto=self.producto_slow
        )

        resultado_non = resultados.get(
            producto=self.producto_non
        )

        self.assertEqual(
            resultado_fast.frecuencia,
            6,
        )

        self.assertAlmostEqual(
            float(resultado_fast.probabilidad),
            0.60,
            places=5,
        )

        self.assertEqual(
            resultado_fast.categoria,
            ResultadoClasificacion.Categoria.FAST,
        )

        self.assertEqual(
            resultado_slow.frecuencia,
            3,
        )

        self.assertAlmostEqual(
            float(resultado_slow.probabilidad),
            0.30,
            places=5,
        )

        self.assertEqual(
            resultado_slow.categoria,
            ResultadoClasificacion.Categoria.SLOW,
        )

        self.assertEqual(
            resultado_non.frecuencia,
            1,
        )

        self.assertAlmostEqual(
            float(resultado_non.probabilidad),
            0.10,
            places=5,
        )

        self.assertEqual(
            resultado_non.categoria,
            ResultadoClasificacion.Categoria.NON,
        )

    def test_elimina_resultados_cuando_no_hay_ventas_confirmadas(self):
        ejecutar_clasificacion(
            self.parametro
        )

        self.assertEqual(
            ResultadoClasificacion.objects.filter(
                parametro=self.parametro
            ).count(),
            3,
        )

        self.venta_confirmada.estado = (
            Venta.EstadoVenta.ANULADA
        )

        self.venta_confirmada.save(
            update_fields=[
                "estado",
                "fecha_modificacion",
            ]
        )

        resumen = ejecutar_clasificacion(
            self.parametro
        )

        self.assertEqual(
            resumen,
            {
                "productos": 0,
                "fast": 0,
                "slow": 0,
                "non": 0,
            },
        )

        self.assertFalse(
            ResultadoClasificacion.objects.filter(
                parametro=self.parametro
            ).exists()
        )

class ParametroClasificacionFormTest(TestCase):
    """Pruebas de validación del formulario de clasificación."""

    def obtener_datos_validos(self):
        return {
            "nombre": "Análisis de prueba",
            "fecha_inicio": "2026-07-01",
            "fecha_fin": "2026-07-31",
            "umbral_fast": "0.60",
            "umbral_slow": "0.25",
            "activo": True,
        }

    def test_formulario_acepta_datos_validos(self):
        form = ParametroClasificacionForm(
            data=self.obtener_datos_validos()
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

    def test_rechaza_fecha_inicio_posterior_a_fecha_fin(self):
        datos = self.obtener_datos_validos()

        datos["fecha_inicio"] = "2026-08-01"
        datos["fecha_fin"] = "2026-07-31"

        form = ParametroClasificacionForm(
            data=datos
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertTrue(
            form.errors
        )

    def test_rechaza_umbral_fast_menor_que_slow(self):
        datos = self.obtener_datos_validos()

        datos["umbral_fast"] = "0.20"
        datos["umbral_slow"] = "0.30"

        form = ParametroClasificacionForm(
            data=datos
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertTrue(
            form.errors
        )

    def test_rechaza_umbrales_iguales(self):
        datos = self.obtener_datos_validos()

        datos["umbral_fast"] = "0.30"
        datos["umbral_slow"] = "0.30"

        form = ParametroClasificacionForm(
            data=datos
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertTrue(
            form.errors
        )

class AccesoClasificacionTest(TestCase):
    """Pruebas de acceso al módulo según el rol del usuario."""

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador = Group.objects.create(
            name="Administrador"
        )

        grupo_empleado = Group.objects.create(
            name="Empleado"
        )

        grupo_cliente = Group.objects.create(
            name="Cliente"
        )

        self.administrador = (
            usuario_modelo.objects.create_user(
                username="administrador_prueba",
                password="clave-prueba-123",
            )
        )

        self.administrador.groups.add(
            grupo_administrador
        )

        self.empleado = (
            usuario_modelo.objects.create_user(
                username="empleado_prueba",
                password="clave-prueba-123",
            )
        )

        self.empleado.groups.add(
            grupo_empleado
        )

        self.cliente = (
            usuario_modelo.objects.create_user(
                username="cliente_prueba",
                password="clave-prueba-123",
            )
        )

        self.cliente.groups.add(
            grupo_cliente
        )

        self.superusuario = (
            usuario_modelo.objects.create_superuser(
                username="superusuario_prueba",
                email="superusuario@prueba.com",
                password="clave-prueba-123",
            )
        )

        self.url = reverse(
            "clasificacion:clasificacion_automatica"
        )

    def test_administrador_puede_acceder(self):
        self.client.force_login(
            self.administrador
        )

        respuesta = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

    def test_empleado_puede_acceder(self):
        self.client.force_login(
            self.empleado
        )

        respuesta = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

    def test_superusuario_puede_acceder(self):
        self.client.force_login(
            self.superusuario
        )

        respuesta = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

    def test_cliente_no_puede_acceder(self):
        self.client.force_login(
            self.cliente
        )

        respuesta = self.client.get(
            self.url
        )

        self.assertIn(
            respuesta.status_code,
            [302, 403],
        )

    def test_usuario_sin_sesion_es_redirigido(self):
        respuesta = self.client.get(
            self.url
        )

        self.assertEqual(
            respuesta.status_code,
            302,
        )

class ClasificacionPDFTest(TestCase):
    """Pruebas de acceso y generación del PDF de clasificación."""

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador = Group.objects.create(
            name="Administrador"
        )

        grupo_empleado = Group.objects.create(
            name="Empleado"
        )

        grupo_cliente = Group.objects.create(
            name="Cliente"
        )

        self.administrador = (
            usuario_modelo.objects.create_user(
                username="admin_pdf",
                password="clave-prueba-123",
            )
        )

        self.administrador.groups.add(
            grupo_administrador
        )

        self.empleado = (
            usuario_modelo.objects.create_user(
                username="empleado_pdf",
                password="clave-prueba-123",
            )
        )

        self.empleado.groups.add(
            grupo_empleado
        )

        self.cliente = (
            usuario_modelo.objects.create_user(
                username="cliente_pdf",
                password="clave-prueba-123",
            )
        )

        self.cliente.groups.add(
            grupo_cliente
        )

        self.parametro_administrador = (
            ParametroClasificacion.objects.create(
                nombre="Análisis PDF administrador",
                fecha_inicio=date(2026, 7, 1),
                fecha_fin=date(2026, 7, 31),
                umbral_fast=Decimal("0.60"),
                umbral_slow=Decimal("0.25"),
                usuario_registro=self.administrador,
            )
        )

        self.parametro_empleado = (
            ParametroClasificacion.objects.create(
                nombre="Análisis PDF empleado",
                fecha_inicio=date(2026, 7, 1),
                fecha_fin=date(2026, 7, 31),
                umbral_fast=Decimal("0.60"),
                umbral_slow=Decimal("0.25"),
                usuario_registro=self.empleado,
            )
        )

        self.parametro_cliente = (
            ParametroClasificacion.objects.create(
                nombre="Análisis PDF cliente",
                fecha_inicio=date(2026, 7, 1),
                fecha_fin=date(2026, 7, 31),
                umbral_fast=Decimal("0.60"),
                umbral_slow=Decimal("0.25"),
                usuario_registro=self.cliente,
            )
        )

    def obtener_url_pdf(self, parametro):
        return reverse(
            "clasificacion:clasificacion_pdf",
            args=[parametro.id],
        )

    def test_administrador_puede_descargar_pdf(self):
        self.client.force_login(
            self.administrador
        )

        respuesta = self.client.get(
            self.obtener_url_pdf(
                self.parametro_administrador
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf",
        )

        self.assertTrue(
            respuesta.content.startswith(
                b"%PDF"
            )
        )

        self.assertIn(
            "attachment;",
            respuesta["Content-Disposition"],
        )

    def test_empleado_puede_descargar_pdf(self):
        self.client.force_login(
            self.empleado
        )

        respuesta = self.client.get(
            self.obtener_url_pdf(
                self.parametro_empleado
            )
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta["Content-Type"],
            "application/pdf",
        )

        self.assertTrue(
            respuesta.content.startswith(
                b"%PDF"
            )
        )

    def test_cliente_no_puede_descargar_pdf(self):
        self.client.force_login(
            self.cliente
        )

        respuesta = self.client.get(
            self.obtener_url_pdf(
                self.parametro_cliente
            )
        )

        self.assertIn(
            respuesta.status_code,
            [302, 403],
        )

    def test_usuario_sin_sesion_no_puede_descargar_pdf(self):
        respuesta = self.client.get(
            self.obtener_url_pdf(
                self.parametro_administrador
            )
        )

        self.assertEqual(
            respuesta.status_code,
            302,
        )

class FiltrosClasificacionTest(TestCase):
    """Pruebas de filtros y ordenamiento de clasificación."""

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador = Group.objects.create(
            name="Administrador"
        )

        self.usuario = usuario_modelo.objects.create_user(
            username="admin_filtros",
            password="clave-prueba-123",
        )

        self.usuario.groups.add(
            grupo_administrador
        )

        self.cliente = Cliente.objects.create(
            nombre="Cliente filtros",
            documento="FILTROS-001",
        )

        tipos = list(
            Producto._meta
            .get_field("tipo")
            .choices
        )

        condiciones = list(
            Producto._meta
            .get_field("condicion")
            .choices
        )

        self.tipo_1 = tipos[0][0]

        self.tipo_2 = (
            tipos[1][0]
            if len(tipos) > 1
            else tipos[0][0]
        )

        self.condicion_1 = condiciones[0][0]

        self.condicion_2 = (
            condiciones[1][0]
            if len(condiciones) > 1
            else condiciones[0][0]
        )

        self.producto_fast = Producto.objects.create(
            codigo="FIL-FAST",
            nombre="Pastilla de freno",
            tipo=self.tipo_1,
            condicion=self.condicion_1,
            marca="Marca A",
            precio_compra=Decimal("50.00"),
            precio_venta=Decimal("80.00"),
            stock_actual=3,
            stock_minimo=5,
        )

        self.producto_slow = Producto.objects.create(
            codigo="FIL-SLOW",
            nombre="Filtro de aceite",
            tipo=self.tipo_2,
            condicion=self.condicion_1,
            marca="Marca B",
            precio_compra=Decimal("40.00"),
            precio_venta=Decimal("65.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.producto_non = Producto.objects.create(
            codigo="FIL-NON",
            nombre="Correa auxiliar",
            tipo=self.tipo_1,
            condicion=self.condicion_2,
            marca="Marca C",
            precio_compra=Decimal("25.00"),
            precio_venta=Decimal("45.00"),
            stock_actual=10,
            stock_minimo=3,
        )

        venta = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=timezone.localdate(),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-FILTROS-001",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_fast,
            cantidad=6,
            precio_unitario=Decimal("80.00"),
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_slow,
            cantidad=3,
            precio_unitario=Decimal("65.00"),
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_non,
            cantidad=1,
            precio_unitario=Decimal("45.00"),
        )

        self.url = reverse(
            "clasificacion:clasificacion_automatica"
        )

        self.client.force_login(
            self.usuario
        )

    def obtener_resultados(self, parametros=None):
        respuesta = self.client.get(
            self.url,
            parametros or {},
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        return list(
            respuesta.context["resultados"]
        )

    def test_busqueda_por_codigo(self):
        resultados = self.obtener_resultados(
            {
                "periodo": "semana",
                "busqueda": "FIL-SLOW",
            }
        )

        self.assertEqual(
            len(resultados),
            1,
        )

        self.assertEqual(
            resultados[0].producto,
            self.producto_slow,
        )

    def test_combina_marca_tipo_condicion_y_categoria(self):
        resultados = self.obtener_resultados(
            {
                "periodo": "semana",
                "marca": "Marca A",
                "tipo": self.tipo_1,
                "condicion": self.condicion_1,
                "categoria": "FAST",
            }
        )

        self.assertEqual(
            len(resultados),
            1,
        )

        self.assertEqual(
            resultados[0].producto,
            self.producto_fast,
        )

        self.assertEqual(
            resultados[0].categoria,
            "FAST",
        )

    def test_filtra_productos_de_compra_urgente(self):
        resultados = self.obtener_resultados(
            {
                "periodo": "semana",
                "reposicion": "urgente",
            }
        )

        self.assertEqual(
            len(resultados),
            1,
        )

        self.assertEqual(
            resultados[0].producto,
            self.producto_fast,
        )

    def test_ordena_por_menor_stock(self):
        resultados = self.obtener_resultados(
            {
                "periodo": "semana",
                "orden": "menor_stock",
            }
        )

        stocks = [
            resultado.producto.stock_actual
            for resultado in resultados
        ]

        self.assertEqual(
            stocks,
            sorted(stocks),
        )

        self.assertEqual(
            resultados[0].producto,
            self.producto_fast,
        )

class PeriodosClasificacionTest(TestCase):
    """Pruebas de semana, mes, año y período personalizado."""

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador, _ = Group.objects.get_or_create(
            name="Administrador"
        )

        self.usuario = usuario_modelo.objects.create_user(
            username="admin_periodos",
            password="clave-prueba-123",
        )

        self.usuario.groups.add(
            grupo_administrador
        )

        self.cliente = Cliente.objects.create(
            nombre="Cliente períodos",
            documento="PERIODOS-001",
        )

        tipo = (
            Producto._meta
            .get_field("tipo")
            .choices[0][0]
        )

        condicion = (
            Producto._meta
            .get_field("condicion")
            .choices[0][0]
        )

        self.producto = Producto.objects.create(
            codigo="PER-001",
            nombre="Producto para períodos",
            tipo=tipo,
            condicion=condicion,
            marca="Marca períodos",
            precio_compra=Decimal("30.00"),
            precio_venta=Decimal("50.00"),
            stock_actual=10,
            stock_minimo=3,
        )

        self.hoy = timezone.localdate()

        venta_actual = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=self.hoy,
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-PERIODO-ACTUAL",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta_actual,
            producto=self.producto,
            cantidad=4,
            precio_unitario=Decimal("50.00"),
        )

        # Esta venta servirá para comprobar que el período
        # personalizado excluye registros fuera de sus fechas.
        venta_anterior = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=self.hoy - timedelta(days=10),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-PERIODO-ANTERIOR",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta_anterior,
            producto=self.producto,
            cantidad=7,
            precio_unitario=Decimal("50.00"),
        )

        self.url = reverse(
            "clasificacion:clasificacion_automatica"
        )

        self.client.force_login(
            self.usuario
        )

    def test_periodo_semana(self):
        respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        inicio_semana = (
            self.hoy
            - timedelta(days=self.hoy.weekday())
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.context["periodo_seleccionado"],
            "semana",
        )

        self.assertEqual(
            respuesta.context["fecha_inicio_analisis"],
            inicio_semana,
        )

        self.assertEqual(
            respuesta.context["fecha_fin_analisis"],
            self.hoy,
        )

    def test_periodo_mes(self):
        respuesta = self.client.get(
            self.url,
            {
                "periodo": "mes",
            },
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.context["periodo_seleccionado"],
            "mes",
        )

        self.assertEqual(
            respuesta.context["fecha_inicio_analisis"],
            self.hoy.replace(day=1),
        )

        self.assertEqual(
            respuesta.context["fecha_fin_analisis"],
            self.hoy,
        )

    def test_periodo_anio(self):
        respuesta = self.client.get(
            self.url,
            {
                "periodo": "anio",
            },
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.context["periodo_seleccionado"],
            "anio",
        )

        self.assertEqual(
            respuesta.context["fecha_inicio_analisis"],
            self.hoy.replace(
                month=1,
                day=1,
            ),
        )

        self.assertEqual(
            respuesta.context["fecha_fin_analisis"],
            self.hoy,
        )

    def test_periodo_personalizado_respeta_fechas(self):
        respuesta = self.client.post(
            self.url,
            {
                "nombre": "Análisis personalizado prueba",
                "fecha_inicio": self.hoy.isoformat(),
                "fecha_fin": self.hoy.isoformat(),
                "umbral_fast": "0.60",
                "umbral_slow": "0.25",
                "activo": True,
            },
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        self.assertEqual(
            respuesta.context["periodo_seleccionado"],
            "personalizado",
        )

        resultados = list(
            respuesta.context["resultados"]
        )

        self.assertEqual(
            len(resultados),
            1,
        )

        # Solo debe considerar las 4 unidades vendidas hoy.
        # Las 7 unidades de hace 10 días quedan excluidas.
        self.assertEqual(
            resultados[0].frecuencia,
            4,
        )

class RecalculoClasificacionTest(TestCase):
    """
    Prueba análisis sin ventas y recálculos repetidos.
    """

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador, _ = (
            Group.objects.get_or_create(
                name="Administrador"
            )
        )

        self.usuario = (
            usuario_modelo.objects.create_user(
                username="admin_recalculo",
                password="clave-prueba-123",
            )
        )

        self.usuario.groups.add(
            grupo_administrador
        )

        self.cliente = Cliente.objects.create(
            nombre="Cliente recálculo",
            documento="RECALCULO-001",
        )

        tipo = (
            Producto._meta
            .get_field("tipo")
            .choices[0][0]
        )

        condicion = (
            Producto._meta
            .get_field("condicion")
            .choices[0][0]
        )

        self.producto = Producto.objects.create(
            codigo="REC-001",
            nombre="Producto para recálculo",
            tipo=tipo,
            condicion=condicion,
            marca="Marca recálculo",
            precio_compra=Decimal("30.00"),
            precio_venta=Decimal("50.00"),
            stock_actual=10,
            stock_minimo=3,
        )

        self.url = reverse(
            "clasificacion:clasificacion_automatica"
        )

        self.client.force_login(
            self.usuario
        )

    def test_periodo_sin_ventas_muestra_resultados_vacios(self):
        respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        resultados = list(
            respuesta.context["resultados"]
        )

        self.assertEqual(
            resultados,
            [],
        )

        self.assertEqual(
            respuesta.context["resumen"]["total_unidades"],
            0,
        )

        self.assertEqual(
            respuesta.context["resumen"]["productos_diferentes"],
            0,
        )

    def test_repetir_analisis_no_duplica_parametros_ni_resultados(self):
        venta = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=timezone.localdate(),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-RECALCULO-001",
            usuario_registro=self.usuario,
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=5,
            precio_unitario=Decimal("50.00"),
        )

        primera_respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        segunda_respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        self.assertEqual(
            primera_respuesta.status_code,
            200,
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            200,
        )

        parametros = (
            ParametroClasificacion.objects
            .filter(
                usuario_registro=self.usuario
            )
        )

        self.assertEqual(
            parametros.count(),
            1,
        )

        parametro = parametros.first()

        resultados = (
            ResultadoClasificacion.objects
            .filter(
                parametro=parametro
            )
        )

        self.assertEqual(
            resultados.count(),
            1,
        )

        resultado = resultados.first()

        self.assertEqual(
            resultado.producto,
            self.producto,
        )

        self.assertEqual(
            resultado.frecuencia,
            5,
        )
    def test_recalculo_actualiza_frecuencia_y_categoria(self):
        otro_producto = Producto.objects.create(
            codigo="REC-002",
            nombre="Segundo producto para recálculo",
            tipo=(
                Producto._meta
                .get_field("tipo")
                .choices[0][0]
            ),
            condicion=(
                Producto._meta
                .get_field("condicion")
                .choices[0][0]
            ),
            marca="Marca recálculo",
            precio_compra=Decimal("25.00"),
            precio_venta=Decimal("40.00"),
            stock_actual=10,
            stock_minimo=3,
        )

        venta = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=timezone.localdate(),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-RECALCULO-002",
            usuario_registro=self.usuario,
        )

        detalle_principal = DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=6,
            precio_unitario=Decimal("50.00"),
        )

        DetalleVenta.objects.create(
            venta=venta,
            producto=otro_producto,
            cantidad=4,
            precio_unitario=Decimal("40.00"),
        )

        # Primer cálculo:
        # 6 / 10 = 0.60 → FAST
        primera_respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        self.assertEqual(
            primera_respuesta.status_code,
            200,
        )

        parametro = (
            ParametroClasificacion.objects
            .filter(
                usuario_registro=self.usuario
            )
            .first()
        )

        resultado_inicial = (
            ResultadoClasificacion.objects
            .get(
                parametro=parametro,
                producto=self.producto,
            )
        )

        self.assertEqual(
            resultado_inicial.frecuencia,
            6,
        )

        self.assertEqual(
            resultado_inicial.categoria,
            ResultadoClasificacion.Categoria.FAST,
        )

        # Cambiamos la cantidad vendida.
        detalle_principal.cantidad = 2

        detalle_principal.save(
            update_fields=[
                "cantidad",
            ]
        )

        # Segundo cálculo:
        # 2 / 6 = 0.333... → SLOW
        segunda_respuesta = self.client.get(
            self.url,
            {
                "periodo": "semana",
            },
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            200,
        )

        resultado_actualizado = (
            ResultadoClasificacion.objects
            .get(
                parametro=parametro,
                producto=self.producto,
            )
        )

        self.assertEqual(
            resultado_actualizado.frecuencia,
            2,
        )

        self.assertAlmostEqual(
            float(resultado_actualizado.probabilidad),
            2 / 6,
            places=5,
        )

        self.assertEqual(
            resultado_actualizado.categoria,
            ResultadoClasificacion.Categoria.SLOW,
        )

        # Debe seguir existiendo un único resultado
        # para el producto y parámetro.
        cantidad_resultados = (
            ResultadoClasificacion.objects
            .filter(
                parametro=parametro,
                producto=self.producto,
            )
            .count()
        )

        self.assertEqual(
            cantidad_resultados,
            1,
        )
class AislamientoUsuariosClasificacionTest(TestCase):
    """
    Verifica que cada usuario tenga sus propios análisis
    y no pueda descargar análisis ajenos.
    """

    def setUp(self):
        usuario_modelo = get_user_model()

        grupo_administrador, _ = (
            Group.objects.get_or_create(
                name="Administrador"
            )
        )

        self.usuario_uno = (
            usuario_modelo.objects.create_user(
                username="admin_usuario_uno",
                password="clave-prueba-123",
            )
        )

        self.usuario_uno.groups.add(
            grupo_administrador
        )

        self.usuario_dos = (
            usuario_modelo.objects.create_user(
                username="admin_usuario_dos",
                password="clave-prueba-123",
            )
        )

        self.usuario_dos.groups.add(
            grupo_administrador
        )

        self.url_clasificacion = reverse(
            "clasificacion:clasificacion_automatica"
        )

    def test_cada_usuario_tiene_su_parametro_automatico(self):
        self.client.force_login(
            self.usuario_uno
        )

        respuesta_uno = self.client.get(
            self.url_clasificacion,
            {
                "periodo": "semana",
            },
        )

        self.client.logout()

        self.client.force_login(
            self.usuario_dos
        )

        respuesta_dos = self.client.get(
            self.url_clasificacion,
            {
                "periodo": "semana",
            },
        )

        self.assertEqual(
            respuesta_uno.status_code,
            200,
        )

        self.assertEqual(
            respuesta_dos.status_code,
            200,
        )

        parametros_usuario_uno = (
            ParametroClasificacion.objects
            .filter(
                usuario_registro=self.usuario_uno
            )
        )

        parametros_usuario_dos = (
            ParametroClasificacion.objects
            .filter(
                usuario_registro=self.usuario_dos
            )
        )

        self.assertEqual(
            parametros_usuario_uno.count(),
            1,
        )

        self.assertEqual(
            parametros_usuario_dos.count(),
            1,
        )

        self.assertNotEqual(
            parametros_usuario_uno.first().id,
            parametros_usuario_dos.first().id,
        )

    def test_usuario_no_puede_descargar_pdf_ajeno(self):
        parametro_ajeno = (
            ParametroClasificacion.objects.create(
                nombre="Análisis privado usuario uno",
                fecha_inicio=date(2026, 7, 1),
                fecha_fin=date(2026, 7, 31),
                umbral_fast=Decimal("0.60"),
                umbral_slow=Decimal("0.25"),
                usuario_registro=self.usuario_uno,
            )
        )

        self.client.force_login(
            self.usuario_dos
        )

        url_pdf = reverse(
            "clasificacion:clasificacion_pdf",
            args=[
                parametro_ajeno.id
            ],
        )

        respuesta = self.client.get(
            url_pdf
        )

        self.assertEqual(
            respuesta.status_code,
            404,
        )

class LimitesClasificacionTest(TestCase):
    """
    Verifica la clasificación en los límites exactos
    de los umbrales establecidos.
    """

    def setUp(self):
        usuario_modelo = get_user_model()

        self.usuario = usuario_modelo.objects.create_user(
            username="usuario_limites",
            password="clave-prueba-123",
        )

        self.cliente = Cliente.objects.create(
            nombre="Cliente límites",
            documento="LIMITES-001",
        )

        tipo = (
            Producto._meta
            .get_field("tipo")
            .choices[0][0]
        )

        condicion = (
            Producto._meta
            .get_field("condicion")
            .choices[0][0]
        )

        self.producto_fast = Producto.objects.create(
            codigo="LIM-FAST",
            nombre="Producto límite FAST",
            tipo=tipo,
            condicion=condicion,
            marca="Marca límites",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.producto_slow = Producto.objects.create(
            codigo="LIM-SLOW",
            nombre="Producto límite SLOW",
            tipo=tipo,
            condicion=condicion,
            marca="Marca límites",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.producto_non = Producto.objects.create(
            codigo="LIM-NON",
            nombre="Producto límite NON",
            tipo=tipo,
            condicion=condicion,
            marca="Marca límites",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.producto_sin_ventas = Producto.objects.create(
            codigo="LIM-SIN-VENTAS",
            nombre="Producto sin ventas",
            tipo=tipo,
            condicion=condicion,
            marca="Marca límites",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=20,
            stock_minimo=5,
        )

        self.parametro = ParametroClasificacion.objects.create(
            nombre="Prueba de límites",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            umbral_fast=Decimal("0.60"),
            umbral_slow=Decimal("0.25"),
            usuario_registro=self.usuario,
        )

        venta = Venta.objects.create(
            cliente=self.cliente,
            fecha_venta=date(2026, 7, 15),
            estado=Venta.EstadoVenta.CONFIRMADA,
            forma_pago=Venta.FormaPago.EFECTIVO,
            numero_comprobante="VENTA-LIMITES-001",
            usuario_registro=self.usuario,
        )

        # Total vendido: 20 unidades.
        # 12 / 20 = 0.60
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_fast,
            cantidad=12,
            precio_unitario=Decimal("35.00"),
        )

        # 5 / 20 = 0.25
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_slow,
            cantidad=5,
            precio_unitario=Decimal("35.00"),
        )

        # 3 / 20 = 0.15
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto_non,
            cantidad=3,
            precio_unitario=Decimal("35.00"),
        )

    def test_clasifica_correctamente_en_limites_exactos(self):
        ejecutar_clasificacion(
            self.parametro
        )

        resultado_fast = (
            ResultadoClasificacion.objects.get(
                parametro=self.parametro,
                producto=self.producto_fast,
            )
        )

        resultado_slow = (
            ResultadoClasificacion.objects.get(
                parametro=self.parametro,
                producto=self.producto_slow,
            )
        )

        resultado_non = (
            ResultadoClasificacion.objects.get(
                parametro=self.parametro,
                producto=self.producto_non,
            )
        )

        self.assertAlmostEqual(
            float(resultado_fast.probabilidad),
            0.60,
            places=5,
        )

        self.assertEqual(
            resultado_fast.categoria,
            ResultadoClasificacion.Categoria.FAST,
        )

        self.assertAlmostEqual(
            float(resultado_slow.probabilidad),
            0.25,
            places=5,
        )

        self.assertEqual(
            resultado_slow.categoria,
            ResultadoClasificacion.Categoria.SLOW,
        )

        self.assertAlmostEqual(
            float(resultado_non.probabilidad),
            0.15,
            places=5,
        )

        self.assertEqual(
            resultado_non.categoria,
            ResultadoClasificacion.Categoria.NON,
        )

    def test_producto_sin_ventas_no_se_clasifica(self):
        ejecutar_clasificacion(
            self.parametro
        )

        existe_resultado = (
            ResultadoClasificacion.objects
            .filter(
                parametro=self.parametro,
                producto=self.producto_sin_ventas,
            )
            .exists()
        )

        self.assertFalse(
            existe_resultado
        )

class MetodosResultadoClasificacionTest(TestCase):
    """
    Prueba los nombres comerciales y las recomendaciones
    del resultado de clasificación.
    """

    def setUp(self):
        usuario_modelo = get_user_model()

        self.usuario = usuario_modelo.objects.create_user(
            username="usuario_metodos",
            password="clave-prueba-123",
        )

        tipo = (
            Producto._meta
            .get_field("tipo")
            .choices[0][0]
        )

        condicion = (
            Producto._meta
            .get_field("condicion")
            .choices[0][0]
        )

        self.producto_stock_bajo = Producto.objects.create(
            codigo="MET-BAJO",
            nombre="Producto con stock bajo",
            tipo=tipo,
            condicion=condicion,
            marca="Marca prueba",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=2,
            stock_minimo=5,
        )

        self.producto_stock_suficiente = Producto.objects.create(
            codigo="MET-SUFICIENTE",
            nombre="Producto con stock suficiente",
            tipo=tipo,
            condicion=condicion,
            marca="Marca prueba",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=10,
            stock_minimo=5,
        )

        self.producto_agotado = Producto.objects.create(
            codigo="MET-AGOTADO",
            nombre="Producto agotado",
            tipo=tipo,
            condicion=condicion,
            marca="Marca prueba",
            precio_compra=Decimal("20.00"),
            precio_venta=Decimal("35.00"),
            stock_actual=0,
            stock_minimo=5,
        )

        self.parametro = ParametroClasificacion.objects.create(
            nombre="Prueba de métodos comerciales",
            fecha_inicio=date(2026, 7, 1),
            fecha_fin=date(2026, 7, 31),
            umbral_fast=Decimal("0.60"),
            umbral_slow=Decimal("0.25"),
            usuario_registro=self.usuario,
        )

    def crear_resultado(
        self,
        producto,
        categoria,
    ):
        return ResultadoClasificacion.objects.create(
            parametro=self.parametro,
            producto=producto,
            frecuencia=1,
            probabilidad=Decimal("0.10"),
            categoria=categoria,
        )

    def test_nombres_de_nivel_de_salida(self):
        resultado_fast = self.crear_resultado(
            self.producto_stock_bajo,
            ResultadoClasificacion.Categoria.FAST,
        )

        resultado_slow = self.crear_resultado(
            self.producto_stock_suficiente,
            ResultadoClasificacion.Categoria.SLOW,
        )

        resultado_non = self.crear_resultado(
            self.producto_agotado,
            ResultadoClasificacion.Categoria.NON,
        )

        self.assertEqual(
            resultado_fast.obtener_nivel_salida(),
            "Muy vendido",
        )

        self.assertEqual(
            resultado_slow.obtener_nivel_salida(),
            "Venta moderada",
        )

        self.assertEqual(
            resultado_non.obtener_nivel_salida(),
            "Poco vendido",
        )

    def test_fast_con_stock_bajo_recomienda_compra_urgente(self):
        resultado = self.crear_resultado(
            self.producto_stock_bajo,
            ResultadoClasificacion.Categoria.FAST,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "Comprar urgentemente",
        )

    def test_fast_con_stock_suficiente_recomienda_mantener(self):
        resultado = self.crear_resultado(
            self.producto_stock_suficiente,
            ResultadoClasificacion.Categoria.FAST,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "Mantener abastecido",
        )

    def test_slow_con_stock_bajo_recomienda_reponer(self):
        resultado = self.crear_resultado(
            self.producto_stock_bajo,
            ResultadoClasificacion.Categoria.SLOW,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "Reponer pronto",
        )

    def test_slow_con_stock_suficiente_recomienda_mantener(self):
        resultado = self.crear_resultado(
            self.producto_stock_suficiente,
            ResultadoClasificacion.Categoria.SLOW,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "Mantener stock",
        )

    def test_non_agotado_recomienda_revisar(self):
        resultado = self.crear_resultado(
            self.producto_agotado,
            ResultadoClasificacion.Categoria.NON,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "Revisar antes de comprar",
        )

    def test_non_con_stock_recomienda_no_comprar(self):
        resultado = self.crear_resultado(
            self.producto_stock_suficiente,
            ResultadoClasificacion.Categoria.NON,
        )

        self.assertEqual(
            resultado.obtener_recomendacion(),
            "No comprar por ahora",
        )